/**
 * Google Apps Script — Meeting Time Trigger (v3, 30-minute interval)
 *
 * Setup:
 * 1. Buka https://script.google.com (login: yusuf.consultan@gmail.com)
 * 2. Paste COPY-PASTE.gs (versi lengkap) ATAU isi URL/token di bawah
 * 3. Jalankan setupTriggers() → authorize
 * 4. Jalankan testWebhook()
 *
 * Interval: 30 menit | Lookahead: 35 menit
 */

const CALENDAR_EMAIL = 'yusuf.consultan@gmail.com';
const CHECK_INTERVAL_MIN = 30;
const LOOKAHEAD_MINUTES = 35;

function getWebhookConfig() {
  const props = PropertiesService.getScriptProperties();
  return {
    url: props.getProperty('CURSOR_WEBHOOK_URL'),
    token: props.getProperty('CURSOR_WEBHOOK_TOKEN'),
    localUrl: props.getProperty('LOCAL_WEBHOOK_URL') || '',
  };
}

function setupWebhookConfig() {
  const props = PropertiesService.getScriptProperties();
  props.setProperties({
    'CURSOR_WEBHOOK_URL': 'PASTE_WEBHOOK_URL_HERE',
    'CURSOR_WEBHOOK_TOKEN': 'PASTE_TOKEN_HERE',
    'LOCAL_WEBHOOK_URL': '',
  });
  Logger.log('Webhook config saved.');
}

function checkUpcomingMeetings() {
  const config = getWebhookConfig();
  if (!config.url || !config.token) {
    Logger.log('ERROR: Run setupWebhookConfig() first.');
    return;
  }

  const now = new Date();
  const soon = new Date(now.getTime() + LOOKAHEAD_MINUTES * 60 * 1000);
  const events = CalendarApp.getDefaultCalendar().getEvents(now, soon);
  const props = PropertiesService.getScriptProperties();

  events.forEach(function(event) {
    const firedKey = 'fired_' + event.getId() + '_' + event.getStartTime().getTime();
    if (props.getProperty(firedKey)) return;

    const title = event.getTitle();
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
    if (!meetingUrl) return;

    const payload = {
      event: 'meeting_start',
      title: title,
      start: event.getStartTime().toISOString(),
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
      if (response.getResponseCode() >= 200 && response.getResponseCode() < 300) {
        props.setProperty(firedKey, 'true');
      }
    } catch (e) {
      Logger.log('Cursor webhook failed: ' + e);
    }
  });
}

function setupTriggers() {
  ScriptApp.getProjectTriggers().forEach(function(trigger) {
    ScriptApp.deleteTrigger(trigger);
  });
  ScriptApp.newTrigger('checkUpcomingMeetings')
    .timeBased()
    .everyMinutes(CHECK_INTERVAL_MIN)
    .create();
  Logger.log('Trigger: every ' + CHECK_INTERVAL_MIN + ' min, lookahead ' + LOOKAHEAD_MINUTES + ' min');
}

function testWebhook() {
  const config = getWebhookConfig();
  if (!config.url || !config.token) {
    Logger.log('ERROR: Run setupWebhookConfig() first.');
    return;
  }
  const response = UrlFetchApp.fetch(config.url, {
    method: 'post',
    contentType: 'application/json',
    headers: { 'Authorization': 'Bearer ' + config.token },
    payload: JSON.stringify({
      event: 'meeting_start',
      title: 'Test Meeting',
      start: new Date().toISOString(),
      url: 'https://zoom.us/j/1234567890',
      calendar_email: CALENDAR_EMAIL,
    }),
    muteHttpExceptions: true,
  });
  Logger.log('Status: ' + response.getResponseCode());
  Logger.log('Response: ' + response.getContentText());
}
