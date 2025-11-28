# Monthly Fee Reminder Setup Guide

## Overview

Automatic WhatsApp reminders are sent to members with unpaid fees every month at your scheduled time.

## Features

- ✅ Automatic daily check for unpaid members
- ✅ WhatsApp message reminders
- ✅ Customizable reminder time
- ✅ Manual "Send Now" option
- ✅ Dashboard toggle to enable/disable

## Setup Steps

### 1. Configure WhatsApp (Required)

Set these environment variables or add to `.env`:

```bash
# WhatsApp Cloud API Configuration
WHATSAPP_TOKEN=your_whatsapp_cloud_api_token
WHATSAPP_PHONE_NUMBER_ID=your_business_phone_number_id
WHATSAPP_DEFAULT_COUNTRY_CODE=92

# Optional: Template-based messages
WHATSAPP_TEMPLATE_FEE_REMINDER_NAME=fee_reminder
WHATSAPP_TEMPLATE_LANG=en
```

**Get WhatsApp Credentials:**

1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Create a WhatsApp Business App
3. Get your Phone Number ID and Access Token

### 2. Enable Reminders in Dashboard

#### Method 1: Dashboard UI (Recommended)

1. Login as admin
2. Open **Dashboard** → Click **Settings**
3. Scroll to **Monthly Reminders** section
4. Toggle **Enable automatic monthly fee reminders**
5. Set reminder time:
   - Hour: 9 (24-hour format: 0-23)
   - Minute: 0
6. Click **Save Reminder Settings**
7. **Restart server** to apply schedule

#### Method 2: Environment Variables

```powershell
# Windows PowerShell
$env:SCHEDULE_REMINDERS_ENABLED = "1"
$env:SCHEDULE_TIME_HH = "9"
$env:SCHEDULE_TIME_MM = "0"
```

```bash
# Linux/Mac
export SCHEDULE_REMINDERS_ENABLED=1
export SCHEDULE_TIME_HH=9
export SCHEDULE_TIME_MM=0
```

### 3. Restart Server

After configuring, restart the Flask server:

```powershell
# Stop current server (Ctrl+C)
python app.py
```

## How It Works

### Automatic Flow

1. **Daily Check**: Server checks at your set time (e.g., 9:00 AM)
2. **Find Unpaid**: Identifies all members with unpaid fees for current month
3. **Send Messages**: Sends WhatsApp reminder to each unpaid member
4. **Track Results**: Logs success/failure count

### Message Content

Default text message format:

```
Hello [Member Name],
This is a reminder that your gym fee for [Month] [Year] is due.
Please make payment at your earliest convenience.
Thank you!
```

Template message (if configured):

- Uses your custom WhatsApp template
- Variables: Member name, Month, Year

### Manual Trigger

Use the **"Send Reminders"** button on dashboard to:

- Test reminder system immediately
- Send reminders outside scheduled time
- Check if WhatsApp configuration works

## Dashboard Features

### Settings Modal

- **Enable/Disable**: Toggle automatic reminders on/off
- **Time Settings**: Set hour (0-23) and minute (0-59)
- **Status Badge**: Shows current state
  - 🟢 Green: "Enabled - Daily at HH:MM"
  - ⚪ Gray: "Disabled"

### Toolbar Button

- **Send Reminders**: Manual trigger
- Shows toast with results: "X sent, Y failed"

## Troubleshooting

### Issue: "Missing: WHATSAPP_TOKEN, WHATSAPP_PHONE_NUMBER_ID"

**Solution**: Set WhatsApp environment variables and restart server

### Issue: Reminders not sending automatically

**Checklist**:

1. ✓ Reminders enabled in Settings modal
2. ✓ Environment variables set correctly
3. ✓ Server restarted after configuration
4. ✓ APScheduler installed: `pip install apscheduler`

### Issue: "Failed to send" messages

**Common causes**:

- Invalid phone numbers (must include country code)
- WhatsApp token expired
- Phone number not verified in Meta dashboard
- Template not approved (if using templates)

### Issue: Schedule not updating

**Solution**: Always restart server after changing reminder time or enable/disable settings

## API Endpoints

### Get Current Settings

```http
GET /admin/settings/reminders
Authorization: Admin login required

Response:
{
  "ok": true,
  "enabled": true,
  "hour": 9,
  "minute": 0
}
```

### Update Settings

```http
POST /admin/settings/reminders
Content-Type: application/json
Authorization: Admin login required

Body:
{
  "enabled": true,
  "hour": 9,
  "minute": 0
}

Response:
{
  "ok": true,
  "message": "Reminder settings saved. Restart server to apply schedule."
}
```

### Manual Trigger

```http
POST /admin/schedule/run-now
Authorization: Admin login required

Response:
{
  "ok": true,
  "sent": 15,
  "failed": 2
}
```

## Technical Details

### Scheduler

- Uses **APScheduler** for background jobs
- Cron trigger: runs daily at specified time
- Timezone: Server system timezone

### Database Tables

- **Member**: Contains phone numbers and admission dates
- **Payment**: Tracks monthly fee status (Paid/Unpaid/N/A)
- **Setting**: Stores reminder configuration

### Code Location

- Scheduler setup: `app.py` → `start_scheduler_once()`
- Reminder job: `app.py` → `send_monthly_unpaid_template_job()`
- Bulk send logic: `app.py` → `send_bulk_template_reminders()` or `send_bulk_text_reminders()`

## Production Deployment

### Render.com

Add environment variables in Render dashboard:

```
SCHEDULE_REMINDERS_ENABLED=1
SCHEDULE_TIME_HH=9
SCHEDULE_TIME_MM=0
WHATSAPP_TOKEN=your_token
WHATSAPP_PHONE_NUMBER_ID=your_id
```

### Heroku

```bash
heroku config:set SCHEDULE_REMINDERS_ENABLED=1
heroku config:set SCHEDULE_TIME_HH=9
heroku config:set SCHEDULE_TIME_MM=0
heroku config:set WHATSAPP_TOKEN=your_token
heroku config:set WHATSAPP_PHONE_NUMBER_ID=your_id
```

## Best Practices

1. **Test First**: Use "Send Reminders" button to test before enabling automatic
2. **Time Selection**: Choose off-peak hours (early morning) to avoid rate limits
3. **Monitor Logs**: Check server logs for send failures
4. **Template Approval**: If using templates, get them approved by Meta first
5. **Phone Format**: Ensure member phones include country code (e.g., +92XXXXXXXXXX)

## Support

For issues or questions:

1. Check WhatsApp status badge on dashboard
2. Review server logs for errors
3. Test with "Send Reminders" button first
4. Verify environment variables are set

---

**Last Updated**: November 26, 2025
**Version**: 1.0
