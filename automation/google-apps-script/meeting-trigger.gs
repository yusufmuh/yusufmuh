/**
 * Google Apps Script — Meeting Time Trigger
 *
 * Setup:
 * 1. Buka https://script.google.com (login: yusuf.consultan@gmail.com)
 * 2. Buat project baru, paste script ini
 * 3. Jalankan setupWebhookConfig() sekali → authorize
 * 4. Jalankan setupTriggers() sekali
 * 5. Jalankan testWebhook() untuk verifikasi
 */

const CALENDAR_EMAIL = 'yusuf.consultan@gmail.com';
const MINUTES_BEFORE = 2;

function getWebhookConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    url: props.getProperty('CURSOR_WEBHOOK_URL'),
    token: props.getProperty('CURSOR_WEBHOOK_TOKEN'),
    localUrl: props.getProperty('LOCAL_WEBHOOK_URL') || '',
  };
}

/**
 * Jalankan SEKALI untuk menyimpan webhook credentials.
 * Ganti nilai di bawah sebelum run.
 */
function setupWebhookConfig() {
  const props = PropertiesService.getScriptProperties();
  props.setProperties({
    'CURSOR_WEBHOOK_URL': 'PASTE_WEBHOOK_URL_HERE',
    'CURSOR_WEBHOOK_TOKEN': 'PASTE_TOKEN_HERE',
    'LOCAL_WEBHOOK_URL': '', // isi URL ngrok jika ada
  });
  Logger.log('Webhook config saved to Script Properties.');
}

function checkUpcomingMeetings() {
  const config = getWebhookConfig();
  if (!config.url || !config.token) {
    Logger.log('ERROR: Run setupWebhookConfig() first.');
    return;
  }

  const now = new Date();
  const soon = new Date(now.getTime() + MINUTES_BEFORE * 60 * 1000);
  const events = CalendarApp.getDefaultCalendar().getEvents(now, soon);
  const props = PropertiesService.getScriptProperties();

  events.forEach(function(event) {
    const eventId = event.getId();
    const firedKey = 'fired_' + eventId;

    if (props.getProperty(firedKey)) {
      return;
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

    try {
      const response = UrlFetchApp.fetch(config.url, {
        method: 'post',
        contentType: 'application/json',
        headers: { 'Authorization': 'Bearer ' + config.token },
        payload: JSON.stringify(payload),
        muteHttpExceptions: true,
      });
      Logger.log('Cursor webhook [' + response.getResponseCode() + ']: ' + title);
    } catch (e) {
      Logger.log('Cursor webhook failed: ' + e);
    }

    if (config.localUrl) {
      try {
        UrlFetchApp.fetch(config.localUrl, {
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
  });
}

function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    ScriptApp.deleteTrigger(trigger);
  });

  ScriptApp.newTrigger('checkUpcomingMeetings')
    .timeBased()
    .everyMinutes(1)
    .create();

  Logger.log('Trigger created: checkUpcomingMeetings every 1 minute');
}

function testWebhook() {
  const config = getWebhookConfig();
  if (!config.url || !config.token) {
    Logger.log('ERROR: Run setupWebhookConfig() first.');
    return;
  }

  const payload = {
    event: 'meeting_start',
    title: 'Test Meeting dari Google Apps Script',
    start: new Date().toISOString(),
    url: 'https://zoom.us/j/1234567890',
    zoom_url: 'https://zoom.us/j/1234567890',
    calendar_email: CALENDAR_EMAIL,
  };

  const response = UrlFetchApp.fetch(config.url, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + config.token },
    payload: JSON.stringify(payload),
    muteHttpExceptions: true,
  });

  Logger.log('Status: ' + response.getResponseCode());
  Logger.log('Response: ' + response.getContentText());
}
