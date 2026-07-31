/**
 * Email Meeting → Google Calendar
 * Account target: yusuf.consultan@gmail.com
 *
 * Cara pakai:
 * 1. Login ke https://script.google.com dengan yusuf.consultan@gmail.com
 * 2. New project → tempel seluruh file ini
 * 3. Jalankan setup() sekali (izinkan Gmail + Calendar)
 * 4. Trigger tiap 15 menit sudah dibuat otomatis oleh setup()
 */

var CONFIG = {
  EXPECTED_ACCOUNT: 'yusuf.consultan@gmail.com',
  TIMEZONE: 'Asia/Jakarta',
  LOOKBACK_DAYS: 7,
  MAX_THREADS: 50,
  DEFAULT_DURATION_MINUTES: 60,
  PROCESSED_LABEL: 'calendar-synced',
  QUERY_BASE:
    'in:inbox newer_than:7d -label:calendar-synced ' +
    '(undangan OR invitation OR invite OR rsvp OR meeting OR interview OR wawancara ' +
    'OR jadwal OR schedule OR appointment OR agenda OR kalender OR calendar OR sync OR call ' +
    'OR "google meet" OR zoom OR "teams.microsoft" OR webex OR calendly OR whereby OR meet.google)',
};

/**
 * One-time setup: validate account, create label, install trigger.
 */
function setup() {
  assertExpectedAccount_();
  getOrCreateLabel_(CONFIG.PROCESSED_LABEL);

  // Remove previous triggers for this function, then install a fresh one.
  ScriptApp.getProjectTriggers().forEach(function (trigger) {
    if (trigger.getHandlerFunction() === 'syncMeetingEmailsToCalendar') {
      ScriptApp.deleteTrigger(trigger);
    }
  });

  ScriptApp.newTrigger('syncMeetingEmailsToCalendar')
    .timeBased()
    .everyMinutes(15)
    .create();

  // First run immediately.
  var result = syncMeetingEmailsToCalendar();
  Logger.log(JSON.stringify(result, null, 2));
}

/**
 * Main automation entrypoint (also used by the time-based trigger).
 */
function syncMeetingEmailsToCalendar() {
  assertExpectedAccount_();

  var label = getOrCreateLabel_(CONFIG.PROCESSED_LABEL);
  var calendar = CalendarApp.getDefaultCalendar();
  var threads = GmailApp.search(CONFIG.QUERY_BASE, 0, CONFIG.MAX_THREADS);

  var created = [];
  var updated = [];
  var skipped = [];
  var clarifications = [];

  threads.forEach(function (thread) {
    var messages = thread.getMessages();
    var message = messages[messages.length - 1];
    var subject = message.getSubject() || '(no subject)';
    var body = (message.getPlainBody() || '') + '\n' + (message.getBody() || '');
    var from = message.getFrom() || '';
    var to = message.getTo() || '';
    var cc = message.getCc() || '';
    var messageId = message.getId();
    var dateHint = message.getDate();

    if (!looksLikeMeeting_(subject, body)) {
      skipped.push({ subject: subject, reason: 'not meeting-related' });
      thread.addLabel(label);
      return;
    }

    var meetingUrl = extractMeetingUrl_(body);
    var parsed = extractDateTime_(subject + '\n' + body, dateHint);

    if (!parsed || !parsed.start) {
      clarifications.push({
        subject: subject,
        reason: 'missing or ambiguous date/time',
        from: from,
        meetingUrl: meetingUrl || null,
      });
      // Do not label yet — retry on later runs in case a follow-up clarifies the time.
      return;
    }

    var end = parsed.end || new Date(parsed.start.getTime() + CONFIG.DEFAULT_DURATION_MINUTES * 60 * 1000);
    var title = cleanTitle_(subject);
    var attendees = collectEmails_([from, to, cc]).filter(function (email) {
      return email.toLowerCase() !== CONFIG.EXPECTED_ACCOUNT.toLowerCase();
    });

    var descriptionParts = [
      'Agenda / catatan dari email:',
      truncate_(stripHtml_(body), 3500),
      '',
      'Source email: ' + subject,
      'From: ' + from,
      'Gmail messageId: ' + messageId,
    ];
    if (meetingUrl) {
      descriptionParts.unshift('Meeting link: ' + meetingUrl, '');
    }
    var description = descriptionParts.join('\n');

    var existing = findExistingEvent_(calendar, title, parsed.start, meetingUrl);
    if (existing) {
      existing.setTitle(title);
      existing.setTime(parsed.start, end);
      existing.setDescription(mergeDescription_(existing.getDescription(), description));
      if (meetingUrl) {
        existing.setLocation(meetingUrl);
      }
      updated.push({
        title: title,
        start: parsed.start.toISOString(),
        end: end.toISOString(),
        eventId: existing.getId(),
        meetingUrl: meetingUrl || null,
      });
    } else {
      var options = { description: description };
      if (meetingUrl) {
        options.location = meetingUrl;
      }
      var event = calendar.createEvent(title, parsed.start, end, options);
      created.push({
        title: title,
        start: parsed.start.toISOString(),
        end: end.toISOString(),
        eventId: event.getId(),
        meetingUrl: meetingUrl || null,
        attendeesHint: attendees,
      });
    }

    thread.addLabel(label);
    try {
      message.markRead();
    } catch (e) {
      // Non-fatal.
    }
  });

  var summary = {
    mailbox: CONFIG.EXPECTED_ACCOUNT,
    timezone: CONFIG.TIMEZONE,
    scannedThreads: threads.length,
    createdCount: created.length,
    updatedCount: updated.length,
    skippedCount: skipped.length,
    clarificationsCount: clarifications.length,
    created: created,
    updated: updated,
    skipped: skipped,
    clarifications: clarifications,
  };

  Logger.log(JSON.stringify(summary, null, 2));
  return summary;
}

/** Manual dry-run helper from the Apps Script editor. */
function dryRunPreview() {
  assertExpectedAccount_();
  var threads = GmailApp.search(CONFIG.QUERY_BASE, 0, 10);
  var preview = threads.map(function (thread) {
    var message = thread.getMessages().pop();
    var subject = message.getSubject() || '(no subject)';
    var body = (message.getPlainBody() || '') + '\n' + (message.getBody() || '');
    return {
      subject: subject,
      from: message.getFrom(),
      meetingUrl: extractMeetingUrl_(body),
      parsed: extractDateTime_(subject + '\n' + body, message.getDate()),
      isMeeting: looksLikeMeeting_(subject, body),
    };
  });
  Logger.log(JSON.stringify(preview, null, 2));
  return preview;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function assertExpectedAccount_() {
  var email = Session.getActiveUser().getEmail();
  if (!email) {
    throw new Error(
      'Tidak bisa membaca akun aktif. Pastikan script dijalankan saat login sebagai ' +
        CONFIG.EXPECTED_ACCOUNT
    );
  }
  if (email.toLowerCase() !== CONFIG.EXPECTED_ACCOUNT.toLowerCase()) {
    throw new Error(
      'Akun aktif adalah ' + email + '. Automation ini khusus untuk ' + CONFIG.EXPECTED_ACCOUNT
    );
  }
}

function getOrCreateLabel_(name) {
  var label = GmailApp.getUserLabelByName(name);
  if (!label) {
    label = GmailApp.createLabel(name);
  }
  return label;
}

function looksLikeMeeting_(subject, body) {
  var text = ((subject || '') + '\n' + (body || '')).toLowerCase();
  var keywords = [
    'undangan',
    'invitation',
    'invite',
    'rsvp',
    'meeting',
    'interview',
    'wawancara',
    'jadwal',
    'schedule',
    'appointment',
    'agenda',
    'kalender',
    'calendar',
    'google meet',
    'zoom.us',
    'zoom.com',
    'teams.microsoft',
    'webex',
    'calendly',
    'whereby',
    'meet.google',
    'join the meeting',
    'bergabung',
    'conference call',
    'video call',
  ];
  for (var i = 0; i < keywords.length; i++) {
    if (text.indexOf(keywords[i]) !== -1) {
      return true;
    }
  }
  return !!extractMeetingUrl_(text);
}

function extractMeetingUrl_(text) {
  if (!text) return null;
  var patterns = [
    /https?:\/\/meet\.google\.com\/[a-z0-9\-]+/i,
    /https?:\/\/[\w.-]*zoom\.us\/j\/\d+[^\s<"']*/i,
    /https?:\/\/[\w.-]*zoom\.com\/j\/\d+[^\s<"']*/i,
    /https?:\/\/teams\.microsoft\.com\/l\/meetup-join\/[^\s<"']+/i,
    /https?:\/\/[\w.-]*webex\.com\/[^\s<"']+/i,
    /https?:\/\/[\w.-]*whereby\.com\/[^\s<"']+/i,
    /https?:\/\/[\w.-]*calendly\.com\/[^\s<"']+/i,
  ];
  for (var i = 0; i < patterns.length; i++) {
    var match = text.match(patterns[i]);
    if (match) {
      return match[0].replace(/[)>,.;]+$/, '');
    }
  }
  return null;
}

/**
 * Best-effort datetime extraction for ID/EN emails.
 * Returns { start: Date, end?: Date } or null.
 */
function extractDateTime_(text, fallbackDate) {
  if (!text) return null;
  var normalized = text.replace(/\r/g, '\n');

  // ISO-like: 2026-07-31 14:00 or 2026/07/31 14:00
  var iso = normalized.match(
    /(\d{4})[\/\-](\d{1,2})[\/\-](\d{1,2})(?:[ T](\d{1,2})[:.](\d{2})(?:\s*(AM|PM|am|pm))?)?/
  );
  if (iso) {
    var startIso = buildDate_(
      Number(iso[1]),
      Number(iso[2]),
      Number(iso[3]),
      Number(iso[4] || 9),
      Number(iso[5] || 0),
      iso[6]
    );
    var endIso = extractEndNear_(normalized, startIso);
    return { start: startIso, end: endIso };
  }

  // ID/EN textual date: 31 Juli 2026 / July 31, 2026
  var idMonths = {
    januari: 1,
    january: 1,
    februari: 2,
    february: 2,
    maret: 3,
    march: 3,
    april: 4,
    mei: 5,
    may: 5,
    juni: 6,
    june: 6,
    juli: 7,
    july: 7,
    agustus: 8,
    august: 8,
    september: 9,
    oktober: 10,
    october: 10,
    november: 11,
    desember: 12,
    december: 12,
  };

  var monthNames = Object.keys(idMonths).join('|');
  var dmy = normalized.match(
    new RegExp(
      '(\\d{1,2})\\s+(' + monthNames + ')\\s+(\\d{4})(?:[^\\d]{0,20}(\\d{1,2})[:.](\\d{2})\\s*(AM|PM|am|pm)?)?',
      'i'
    )
  );
  if (dmy) {
    var startDmy = buildDate_(
      Number(dmy[3]),
      idMonths[dmy[2].toLowerCase()],
      Number(dmy[1]),
      Number(dmy[4] || 9),
      Number(dmy[5] || 0),
      dmy[6]
    );
    return { start: startDmy, end: extractEndNear_(normalized, startDmy) };
  }

  var mdy = normalized.match(
    new RegExp(
      '(' + monthNames + ')\\s+(\\d{1,2})(?:,)?\\s+(\\d{4})(?:[^\\d]{0,20}(\\d{1,2})[:.](\\d{2})\\s*(AM|PM|am|pm)?)?',
      'i'
    )
  );
  if (mdy) {
    var startMdy = buildDate_(
      Number(mdy[3]),
      idMonths[mdy[1].toLowerCase()],
      Number(mdy[2]),
      Number(mdy[4] || 9),
      Number(mdy[5] || 0),
      mdy[6]
    );
    return { start: startMdy, end: extractEndNear_(normalized, startMdy) };
  }

  // Relative day words + time: "besok jam 14:00", "tomorrow at 2pm"
  var relative = normalized.match(
    /\b(hari ini|today|besok|tomorrow|lusa)\b[^\n]{0,40}?(\d{1,2})[:.](\d{2})\s*(AM|PM|am|pm)?/i
  );
  if (relative && fallbackDate) {
    var base = new Date(fallbackDate.getTime());
    var word = relative[1].toLowerCase();
    if (word === 'besok' || word === 'tomorrow') {
      base.setDate(base.getDate() + 1);
    } else if (word === 'lusa') {
      base.setDate(base.getDate() + 2);
    }
    var startRel = buildDate_(
      base.getFullYear(),
      base.getMonth() + 1,
      base.getDate(),
      Number(relative[2]),
      Number(relative[3]),
      relative[4]
    );
    return { start: startRel, end: extractEndNear_(normalized, startRel) };
  }

  // Time range only on email date: "14:00-15:00" / "2:00 PM - 3:00 PM"
  var timeOnly = normalized.match(
    /(\d{1,2})[:.](\d{2})\s*(AM|PM|am|pm)?\s*[-–]\s*(\d{1,2})[:.](\d{2})\s*(AM|PM|am|pm)?/
  );
  if (timeOnly && fallbackDate) {
    var startOnly = buildDate_(
      fallbackDate.getFullYear(),
      fallbackDate.getMonth() + 1,
      fallbackDate.getDate(),
      Number(timeOnly[1]),
      Number(timeOnly[2]),
      timeOnly[3]
    );
    var endOnly = buildDate_(
      fallbackDate.getFullYear(),
      fallbackDate.getMonth() + 1,
      fallbackDate.getDate(),
      Number(timeOnly[4]),
      Number(timeOnly[5]),
      timeOnly[6]
    );
    if (endOnly <= startOnly) {
      endOnly = new Date(endOnly.getTime() + 24 * 60 * 60 * 1000);
    }
    return { start: startOnly, end: endOnly };
  }

  return null;
}

function extractEndNear_(text, start) {
  var range = text.match(
    /(\d{1,2})[:.](\d{2})\s*(AM|PM|am|pm)?\s*[-–]\s*(\d{1,2})[:.](\d{2})\s*(AM|PM|am|pm)?/
  );
  if (!range) return null;
  var end = buildDate_(
    start.getFullYear(),
    start.getMonth() + 1,
    start.getDate(),
    Number(range[4]),
    Number(range[5]),
    range[6]
  );
  if (end <= start) {
    end = new Date(end.getTime() + 24 * 60 * 60 * 1000);
  }
  return end;
}

function buildDate_(year, month, day, hour, minute, ampm) {
  var h = hour;
  if (ampm) {
    var suffix = String(ampm).toUpperCase();
    if (suffix === 'PM' && h < 12) h += 12;
    if (suffix === 'AM' && h === 12) h = 0;
  }
  // Construct in script timezone.
  return new Date(year, month - 1, day, h, minute || 0, 0);
}

function findExistingEvent_(calendar, title, start, meetingUrl) {
  var windowStart = new Date(start.getTime() - 15 * 60 * 1000);
  var windowEnd = new Date(start.getTime() + 15 * 60 * 1000);
  var events = calendar.getEvents(windowStart, windowEnd);
  var normalizedTitle = normalizeTitle_(title);

  for (var i = 0; i < events.length; i++) {
    var event = events[i];
    var sameTitle = normalizeTitle_(event.getTitle()) === normalizedTitle;
    var sameLink =
      meetingUrl &&
      ((event.getLocation() || '').indexOf(meetingUrl) !== -1 ||
        (event.getDescription() || '').indexOf(meetingUrl) !== -1);
    if (sameTitle || sameLink) {
      return event;
    }
  }
  return null;
}

function mergeDescription_(existing, incoming) {
  existing = existing || '';
  if (!existing) return incoming;
  if (existing.indexOf('Gmail messageId:') !== -1 && incoming.indexOf('Gmail messageId:') !== -1) {
    // Replace previous automation block if present.
    return incoming;
  }
  return existing + '\n\n---\n' + incoming;
}

function cleanTitle_(subject) {
  return String(subject || 'Meeting')
    .replace(/^(re|fwd|fw)\s*:\s*/gi, '')
    .replace(/\s+/g, ' ')
    .trim()
    .slice(0, 200);
}

function normalizeTitle_(title) {
  return cleanTitle_(title).toLowerCase();
}

function collectEmails_(chunks) {
  var found = {};
  chunks.forEach(function (chunk) {
    var matches = String(chunk || '').match(/[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}/gi) || [];
    matches.forEach(function (email) {
      found[email.toLowerCase()] = email;
    });
  });
  return Object.keys(found).map(function (key) {
    return found[key];
  });
}

function stripHtml_(html) {
  return String(html || '')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<[^>]+>/g, ' ')
    .replace(/&nbsp;/g, ' ')
    .replace(/&amp;/g, '&')
    .replace(/&lt;/g, '<')
    .replace(/&gt;/g, '>')
    .replace(/\s+/g, ' ')
    .trim();
}

function truncate_(text, max) {
  text = String(text || '');
  if (text.length <= max) return text;
  return text.slice(0, max - 1) + '…';
}
