# Missing endpoints to be added to app.py
# Add these before the "if __name__ == '__main__':" block

# API: Send WhatsApp reminder to individual member
@app.route('/api/members/<int:member_id>/remind', methods=['POST'])
@login_required
def remind_single_member(member_id):
    member = Member.query.get_or_404(member_id)
    now = datetime.now()
    phone = (member.phone or '').strip()
    if not phone:
        return jsonify({"ok": False, "error": "Member has no phone number"}), 400
    
    # Send reminder using WhatsApp template
    template_name = get_setting('whatsapp_template_name') or 'fee_reminder'
    lang = get_setting('whatsapp_template_lang') or 'en'
    month_name = now.strftime('%B')
    body_params = [member.name, month_name, str(now.year)]
    
    ok, msg = send_whatsapp_template(phone, template_name, lang, body_params)
    if ok:
        member.last_contact_at = datetime.now()
        db.session.commit()
        append_audit('member.remind', {'member_id': member_id, 'phone': phone})
        return jsonify({"ok": True, "message": "Reminder sent successfully"})
    return jsonify({"ok": False, "error": msg or "Failed to send reminder"}), 400

# API: Generate and download member card PDF
@app.route('/api/members/<int:member_id>/card', methods=['GET'])
@login_required
def generate_member_card_pdf(member_id):
    member = Member.query.get_or_404(member_id)
    try:
        from io import BytesIO
        from reportlab.lib.pagesizes import A4
        from reportlab.pdfgen import canvas
        from reportlab.lib.units import inch
        
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=A4)
        width, height = A4
        
        # Header
        c.setFont("Helvetica-Bold", 20)
        c.drawCentredString(width/2, height - 1*inch, get_gym_name())
        
        # Member Info
        c.setFont("Helvetica-Bold", 14)
        c.drawString(1*inch, height - 2*inch, "Member Card")
        
        c.setFont("Helvetica", 12)
        y = height - 2.5*inch
        c.drawString(1*inch, y, f"Serial #: {member.serial or member.id}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Name: {member.name}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Phone: {member.phone or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Email: {member.email or 'N/A'}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Admission Date: {member.admission_date}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Plan: {member.plan_type.title()}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Training: {member.display_training_type or member.training_type}")
        y -= 0.3*inch
        c.drawString(1*inch, y, f"Monthly Fee: Rs {member.monthly_fee or 'N/A'}")
        y -= 0.3*inch
        status_text = "Active" if member.is_active else "Inactive"
        c.drawString(1*inch, y, f"Status: {status_text}")
        
        # Footer
        c.setFont("Helvetica", 8)
        c.drawCentredString(width/2, 0.5*inch, f"Generated on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        c.save()
        buffer.seek(0)
        return send_file(buffer, mimetype='application/pdf', as_attachment=True, download_name=f'member_card_{member_id}.pdf')
    except ImportError:
        return jsonify({"ok": False, "error": "reportlab not installed. Run: pip install reportlab"}), 500
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500
