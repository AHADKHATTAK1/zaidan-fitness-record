"""
---------------------------------------------------------
MISSING ENDPOINTS – TEMPLATE (Do not run this file)
---------------------------------------------------------

Purpose:
- This file provides reference implementations of endpoints that may be
  missing from your main Flask application (app.py).
- Copy the functions below into app.py and use your existing imports there.

Why warnings appeared:
- Editors try to resolve imports for this standalone file, but your project
  modules (models, utils, flask_login) are imported from app.py context.
- To avoid false warnings, the entire template is wrapped in a docstring.

How to use:
1) Open app.py.
2) Ensure imports exist:
   from flask import jsonify, send_file
   from flask_login import login_required
   from datetime import datetime
   from io import BytesIO
   from reportlab.lib.pagesizes import A4
   from reportlab.pdfgen import canvas
   from reportlab.lib.units import inch
   # plus: app, db, Member, append_audit, get_setting, get_gym_name, send_whatsapp_template
3) Paste the endpoint functions into app.py.

---------------------------------------------------------
# 1️⃣ API — WhatsApp Reminder to Single Member
---------------------------------------------------------
@app.route('/api/members/<int:member_id>/remind', methods=['POST'])
@login_required
def remind_single_member(member_id):
    member = Member.query.get_or_404(member_id)
    now = datetime.now()

    phone = (member.phone or '').strip()
    if not phone:
        return jsonify({"ok": False, "error": "Member has no phone number"}), 400

    template_name = get_setting('whatsapp_template_name') or 'fee_reminder'
    lang = get_setting('whatsapp_template_lang') or 'en'
    month_name = now.strftime('%B')

    body_params = [member.name, month_name, str(now.year)]

    ok, msg = send_whatsapp_template(phone, template_name, lang, body_params)

    if ok:
        member.last_contact_at = datetime.now()
        db.session.commit()
        append_audit('member.remind', {"member_id": member_id, "phone": phone})
        return jsonify({"ok": True, "message": "Reminder sent successfully"})

    return jsonify({"ok": False, "error": msg or "Failed to send reminder"}), 400


---------------------------------------------------------
# 2️⃣ API — Generate Member Card PDF
---------------------------------------------------------
@app.route('/api/members/<int:member_id>/card', methods=['GET'])
@login_required
def generate_member_card_pdf(member_id):
    member = Member.query.get_or_404(member_id)

    try:
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4

        c.setFont("Helvetica-Bold", 22)
        c.drawCentredString(width / 2, height - 1 * inch, get_gym_name())

        c.setFont("Helvetica-Bold", 16)
        c.drawString(1 * inch, height - 1.8 * inch, "Member Card")

        y = height - 2.4 * inch
        c.setFont("Helvetica", 12)
        info = [
            f"Serial #: {member.serial or member.id}",
            f"Name: {member.name}",
            f"Phone: {member.phone or 'N/A'}",
            f"Email: {member.email or 'N/A'}",
            f"Admission Date: {member.admission_date}",
            f"Plan: {member.plan_type.title()}",
            f"Training: {member.display_training_type or member.training_type}",
            f"Monthly Fee: Rs {member.monthly_fee or 'N/A'}",
            f"Status: {'Active' if member.is_active else 'Inactive'}",
        ]
        for line in info:
            c.drawString(1 * inch, y, line)
            y -= 0.32 * inch

        c.setFont("Helvetica", 8)
        c.drawCentredString(width / 2, 0.55 * inch,
                            f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

        c.save()
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True,
                         download_name=f'member_card_{member_id}.pdf')
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
"""
