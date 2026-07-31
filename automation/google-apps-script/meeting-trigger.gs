/**
 * Google Apps Script — Meeting Time Trigger
 *
 * Setup:
 * 1. Buka https://script.google.com
 * 2. Buat project baru, paste script ini
 * 3. Ganti CURSOR_WEBHOOK_URL dan CURSOR_WEBHOOK_TOKEN
 * 4. Ganti LOCAL_WEBHOOK_URL jika punya tunnel (ngrok/cloudflare)
 * 5. Jalankan setupTriggers() sekali
 * 6. Authorize akses Google Calendar
 */

const CURSOR_WEBHOOK_URL = 'https://api2.cursor.sh/automations/webhook/YOUR_AUTOMATION_ID';
const CURSOR_WEBHOOK_TOKEN = 'crsr_YOUR_TOKEN';
const LOCAL_WEBHOOK_URL = 'http://localhost:8765'; // Ganti dengan ngrok URL jika remote
const CALENDAR_EMAIL = 'yusuf.consultan@gmail.com';
const MINUTES_BEFORE = 2;

/**
 * Check calendar every minute for meetings starting soon.
 */
function checkUpcomingMeetings() {
  const now = new Date();
  const soon = new Date(now.getTime() + MINUTES_BEFORE * 60 * 1000);

  const events = CalendarApp.getDefaultCalendar().getEvents(now, soon);
  const props = PropertiesService.getScriptProperties();

  events.forEach(function(event) {
    const eventId = event.getId();
    const firedKey = 'fired_' + eventId;

    if (props.getProperty(firedKey)) {
      return; // Already fired for this event
    }

    const title = event.getTitle();
    const start = event.getStartTime();
    const location = event.getLocation() || '';
    const description = event.getDescription() || '';

    let meetingUrl = '';
    if (location.startsWith('http')) {
      meetingUrl = location;
    } else {
      const text = description + ' ' + location;
      const zoomMatch = text.match(/https?:\/\/[^\s]*zoom\.us\/[^\s]*/i);
      const meetMatch = text.match(/https?:\/\/meet\.google\.com\/[^\s]*/i);
      const teamsMatch = text.match(/https?:\/\/teams\.(?:microsoft\.com|live\.com)\/[^\s]*/i);
      meetingUrl = (zoomMatch || meetMatch || teamsMatch || [''])[0];
    }

    const payload = {
      event: 'meeting_start',
      title: title,
      start: start.toISOString(),
      url: meetingUrl,
      zoom_url: meetingUrl.indexOf('zoom') >= 0 ? meetingUrl : '',
      location: location,
      calendar_email: CALENDAR_EMAIL,
    };

    // Fire Cursor webhook
    try {
      UrlFetchApp.fetch(CURSOR_WEBHOOK_URL, {
        method: 'post',
        contentType: 'application/json',
        headers: {
          'Authorization': 'Bearer ' + CURSOR_WEBHOOK_TOKEN,
        },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
      });
    } catch (e) {
      Logger.log('Cursor webhook failed: ' + e);
    }

    // Fire local webhook (if tunnel available)
    if (LOCAL_WEBHOOK_URL && LOCAL_WEBHOOK_URL.indexOf('localhost') < 0) {
      try {
        UrlFetchApp.fetch(LOCAL_WEBHOOK_URL, {
          method: 'post',
          contentType: 'application/json',
          payload: JSON.stringify(payload),
          muteHttpExceptions: true,
        });
      } catch (e) {
        Logger.log('Local webhook failed: ' + e);
      }
    }

    props.setProperty(firedKey, 'true');
    Logger.log('Fired webhook for: ' + title);
  });
}

/**
 * Run once to set up the time-driven trigger.
 */
function setupTriggers() {
  // Remove existing triggers
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    ScriptApp.deleteTrigger(trigger);
  });

  // Check every minute
  ScriptApp.newTrigger('checkUpcomingMeetings')
    .timeBased()
    .everyMinutes(1)
    .create();

  Logger.log('Trigger created: checkUpcomingMeetings every 1 minute');
}

/**
 * Manual test — simulates a meeting webhook.
 */
function testWebhook() {
  const payload = {
    event: 'meeting_start',
    title: 'Test Meeting',
    start: new Date().toISOString(),
    url: 'https://zoom.us/j/1234567890',
    zoom_url: 'https://zoom.us/j/1234567890',
    calendar_email: CALENDAR_EMAIL,
  };

  const response = UrlFetchApp.fetch(CURSOR_WEBHOOK_URL, {
    method: 'post',
    contentType: 'application/json',
    headers: {
      'Authorization': 'Bearer ' + CURSOR_WEBHOOK_TOKEN,
    },
    payload: JSON.stringify(payload),
  });

  Logger.log('Response: ' + response.getContentText());
}
