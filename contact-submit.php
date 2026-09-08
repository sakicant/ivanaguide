<?php
/**
 * Contact form endpoint for deborah.hr.
 *
 * Receives the request form from /contact/ and /hr/kontakt/, emails Ivana,
 * and sends the guest a short acknowledgement in their own language.
 * Answers with JSON because the front end submits through fetch().
 *
 * No database and no writable folder in public_html: the only thing written
 * is a rate-limit counter in the system temp directory.
 */

declare(strict_types=1);

const MAIL_TO   = 'ivana@deborah.hr';
const MAIL_FROM = 'ivana@deborah.hr';   // must be a real mailbox on this domain,
                                        // otherwise SPF/DMARC rejects the mail
const FROM_NAME = 'Deborah - deborah.hr';
const MAX_PER_HOUR = 5;                 // submissions allowed per IP per hour

header('Content-Type: application/json; charset=utf-8');
header('X-Content-Type-Options: nosniff');

// mbstring is on almost every host, but fall back rather than fatal if it isn't.
if (!function_exists('mb_substr')) {
    function mb_substr($s, $start, $length = null)
    {
        return $length === null ? substr($s, $start) : substr($s, $start, $length);
    }
}

/** Reply with JSON and stop. */
function respond(int $status, array $payload): void
{
    http_response_code($status);
    echo json_encode($payload, JSON_UNESCAPED_UNICODE);
    exit;
}

/**
 * Mail headers must be ASCII. A Croatian name or subject ("Šime", "Vaš upit")
 * would otherwise arrive as mojibake, so encode anything non-ASCII per RFC 2047.
 */
function mime_header(string $s): string
{
    return preg_match('/[\x80-\xFF]/', $s)
        ? '=?UTF-8?B?' . base64_encode($s) . '?='
        : $s;
}

/**
 * Send mail, naming the envelope sender so the host doesn't fall back to the
 * web-server user (which SPF rejects). Some shared hosts refuse the -f
 * parameter outright, so retry without it before giving up.
 */
function send_mail(string $to, string $subject, string $body, string $headers): bool
{
    if (@mail($to, $subject, $body, $headers, '-f' . MAIL_FROM)) {
        return true;
    }
    return (bool) @mail($to, $subject, $body, $headers);
}

/**
 * A single-line form value: trimmed, length-capped, with CR/LF and NUL
 * removed. Stripping the line breaks is what stops a visitor from injecting
 * extra mail headers through a field that ends up in the subject or headers.
 */
function field(string $key, int $max = 255): string
{
    $v = isset($_POST[$key]) ? trim((string) $_POST[$key]) : '';
    $v = str_replace(["\r", "\n", "\0"], ' ', $v);
    return mb_substr($v, 0, $max);
}

/** A multi-line value: line breaks kept, control characters dropped. */
function textarea(string $key, int $max = 2000): string
{
    $v = isset($_POST[$key]) ? trim((string) $_POST[$key]) : '';
    $v = str_replace("\0", '', $v);
    return mb_substr($v, 0, $max);
}

/**
 * At most MAX_PER_HOUR submissions per IP per hour. The counter lives in the
 * system temp directory and the IP is stored only as a hash, so nothing
 * identifying is kept on disk.
 */
function rate_limit_ok(): bool
{
    $ip = $_SERVER['HTTP_CF_CONNECTING_IP'] ?? $_SERVER['REMOTE_ADDR'] ?? '';
    if ($ip === '') {
        return true;
    }
    $file = sys_get_temp_dir() . '/deborah_cf_' . sha1($ip . date('YmdH')) . '.txt';
    $count = is_readable($file) ? (int) file_get_contents($file) : 0;
    if ($count >= MAX_PER_HOUR) {
        return false;
    }
    @file_put_contents($file, (string) ($count + 1), LOCK_EX);
    return true;
}

// ---------------------------------------------------------------------------

if (($_SERVER['REQUEST_METHOD'] ?? '') !== 'POST') {
    respond(405, ['success' => false, 'error' => 'Method not allowed']);
}

$lang = field('lang', 2) === 'hr' ? 'hr' : 'en';

$MSG = [
    'en' => [
        'rate'    => 'Too many requests from this connection. Please try again later, or message Ivana on WhatsApp.',
        'invalid' => 'Please check the form and try again.',
        'failed'  => 'The message could not be sent. Please use WhatsApp or email instead.',
        'subject' => 'Your tour request - Deborah',
    ],
    'hr' => [
        'rate'    => 'Previše upita s ove veze. Pokušajte kasnije ili se javite Ivani na WhatsApp.',
        'invalid' => 'Molimo provjerite obrazac i pokušajte ponovno.',
        'failed'  => 'Poruku nije bilo moguće poslati. Javite se putem WhatsAppa ili e-pošte.',
        'subject' => 'Vaš upit za turu - Deborah',
    ],
];
$t = $MSG[$lang];

if (!rate_limit_ok()) {
    respond(429, ['success' => false, 'error' => $t['rate']]);
}

// Honeypot. Real visitors never see this field; spam bots fill it with links.
// Only link-like content is rejected, so a browser autofilling the hidden
// "company" field with a harmless company name can't silently drop a real
// enquiry.
if (preg_match('#https?://|www\.#i', field('company'))) {
    respond(200, ['success' => true]);   // look successful to the bot
}

$name      = field('name', 120);
$email     = field('email', 160);
$date      = field('preferred_date', 20);
$time      = field('preferred_time', 20);
$group     = field('group_size', 10);
$message   = textarea('message', 2000);
$consented = !empty($_POST['gdpr_consent']);

$errors = [];
if ($name === '') {
    $errors[] = 'name';
}
if ($email === '' || !filter_var($email, FILTER_VALIDATE_EMAIL)) {
    $errors[] = 'email';
}
if (!$consented) {
    $errors[] = 'gdpr_consent';
}
if ($errors) {
    respond(422, ['success' => false, 'error' => $t['invalid'], 'fields' => $errors]);
}

// ---------------------------------------------------------------------------
// The email to Ivana.
// ---------------------------------------------------------------------------

$when = new DateTime('now', new DateTimeZone('Europe/Zagreb'));

$lines = [
    'Name:        ' . $name,
    'Email:       ' . $email,
    'Language:    ' . ($lang === 'hr' ? 'Croatian' : 'English'),
    'Date wanted: ' . ($date !== '' ? $date : '-'),
    'Time wanted: ' . ($time !== '' ? $time : '-'),
    'Group size:  ' . ($group !== '' ? $group : '-'),
    '',
    'Message:',
    $message !== '' ? $message : '(none)',
    '',
    'Sent:        ' . $when->format('d.m.Y. H:i') . ' (Sibenik time)',
];
$summary = implode("\n", $lines);

// Reply-To carries the address only: the guest's name goes in the body, where
// it doesn't have to survive header encoding.
$headers = 'From: ' . FROM_NAME . ' <' . MAIL_FROM . '>' . "\r\n"
         . 'Reply-To: ' . $email . "\r\n"
         . 'MIME-Version: 1.0' . "\r\n"
         . 'Content-Type: text/plain; charset=utf-8' . "\r\n";

$subject = mime_header('Tour request from ' . $name . ' (' . ($lang === 'hr' ? 'HR' : 'EN') . ')');

if (!send_mail(MAIL_TO, $subject, $summary, $headers)) {
    respond(500, ['success' => false, 'error' => $t['failed']]);
}

// ---------------------------------------------------------------------------
// Acknowledgement to the guest. Best effort: if this one fails the request
// still counts as delivered, because Ivana already has it.
// ---------------------------------------------------------------------------

if ($lang === 'hr') {
    $body = "Poštovani/a " . $name . ",\n\n"
          . "hvala na upitu. Ivana ga je zaprimila i osobno će vam odgovoriti, "
          . "obično unutar nekoliko sati.\n\n"
          . "Vaš upit:\n" . $summary . "\n\n"
          . "Ako nešto nije u redu, samo odgovorite na ovu poruku.\n\n"
          . "Lijep pozdrav,\nIvana Kučić\nDeborah - privatne ture Šibenika\n"
          . "+385 95 527 8924 | ivana@deborah.hr | https://deborah.hr\n";
} else {
    $body = "Hello " . $name . ",\n\n"
          . "thank you for your request. Ivana has received it and will reply "
          . "personally, usually within a few hours.\n\n"
          . "Your request:\n" . $summary . "\n\n"
          . "If anything is wrong, just reply to this email.\n\n"
          . "Best regards,\nIvana Kučić\nDeborah - private tours of Šibenik\n"
          . "+385 95 527 8924 | ivana@deborah.hr | https://deborah.hr\n";
}

$guestHeaders = 'From: ' . FROM_NAME . ' <' . MAIL_FROM . '>' . "\r\n"
              . 'Reply-To: ' . MAIL_TO . "\r\n"
              . 'MIME-Version: 1.0' . "\r\n"
              . 'Content-Type: text/plain; charset=utf-8' . "\r\n";

send_mail($email, mime_header($t['subject']), $body, $guestHeaders);

respond(200, ['success' => true]);
