import os
import sqlite3
from datetime import datetime
import io

import xlsxwriter  # pyright: ignore[reportMissingImports]
from flask import Flask, jsonify, request, send_from_directory, Response
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'bloodbank.db')
FRONTEND_DIR = os.path.join(BASE_DIR, '../frontend')
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

app = Flask(__name__, static_folder=FRONTEND_DIR, static_url_path='/')

# Add CORS headers to allow frontend requests
@app.after_request
def after_request(response):
    response.headers.add('Access-Control-Allow-Origin', '*')
    response.headers.add('Access-Control-Allow-Headers', 'Content-Type,Authorization')
    response.headers.add('Access-Control-Allow-Methods', 'GET,PUT,POST,DELETE,OPTIONS')
    return response

# Serve frontend index.html
@app.route('/')
def index():
    return send_from_directory(FRONTEND_DIR, 'index.html')

# Serve static files (css, js, etc.)
@app.route('/<path:path>')
def static_proxy(path):
    file_path = os.path.join(FRONTEND_DIR, path)
    if os.path.exists(file_path):
        return send_from_directory(FRONTEND_DIR, path)
    return send_from_directory(FRONTEND_DIR, 'index.html')

# --- API ---
@app.route('/api/donors', methods=['GET'])
def list_donors():
    conn = get_db()
    cur = conn.execute('SELECT * FROM donors')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/donors', methods=['POST'])
def add_donor():
    data = request.get_json() or request.form
    fields = ('name','age','blood_group','contact','city','last_donation_date')
    vals = [data.get(f) for f in fields]
    conn = get_db()
    cur = conn.execute('INSERT INTO donors (name,age,blood_group,contact,city,last_donation_date) VALUES (?,?,?,?,?,?)', vals)
    conn.commit()
    donor_id = cur.lastrowid
    conn.close()
    return jsonify({'id': donor_id}), 201

@app.route('/api/requests', methods=['GET'])
def list_requests():
    conn = get_db()
    cur = conn.execute('SELECT * FROM requests ORDER BY created_at DESC')
    rows = [dict(r) for r in cur.fetchall()]
    conn.close()
    return jsonify(rows)

@app.route('/api/requests', methods=['POST'])
def add_request():
    data = request.get_json() or request.form
    fields = ('patient_name','blood_group','units','hospital','city','contact')
    vals = [data.get(f) for f in fields]
    conn = get_db()
    cur = conn.execute('INSERT INTO requests (patient_name,blood_group,units,hospital,city,contact) VALUES (?,?,?,?,?,?)', vals)
    conn.commit()
    req_id = cur.lastrowid
    conn.close()
    return jsonify({'id': req_id}), 201

@app.route('/api/requests/<int:req_id>/status', methods=['PUT'])
def update_request_status(req_id):
    data = request.get_json() or request.form
    status = data.get('status')
    if status not in ('pending', 'approved', 'rejected', 'fulfilled'):
        return jsonify({'error':'invalid status'}), 400
    conn = get_db()
    
    # Update the request status
    conn.execute('UPDATE requests SET status=? WHERE id=?', (status, req_id))
    
    # Find all user_requests linked to this request and create notifications
    cur = conn.execute('''
        SELECT ur.id, ur.user_id, ur.patient_name, ur.blood_group 
        FROM user_requests ur 
        WHERE ur.request_id = ?
    ''', (req_id,))
    user_requests = cur.fetchall()
    
    # Create notifications for each user who made this request
    status_messages = {
        'pending': 'Your blood request is currently pending review by our admin team.',
        'approved': 'Great news! Your blood request has been approved. We will process it shortly.',
        'rejected': 'Unfortunately, your blood request has been rejected. Please contact us for more details.',
        'fulfilled': 'Your blood request has been successfully fulfilled. Thank you for using our service!'
    }
    
    status_titles = {
        'pending': 'Request Pending',
        'approved': 'Request Approved',
        'rejected': 'Request Rejected',
        'fulfilled': 'Request Fulfilled'
    }
    
    notification_types = {
        'pending': 'info',
        'approved': 'success',
        'rejected': 'error',
        'fulfilled': 'success'
    }
    
    for user_req in user_requests:
        user_id = user_req['user_id']
        user_request_id = user_req['id']
        patient_name = user_req['patient_name']
        blood_group = user_req['blood_group']
        
        # Update user_request status as well
        conn.execute('UPDATE user_requests SET status=? WHERE id=?', (status, user_request_id))
        
        # Create notification
        title = status_titles.get(status, 'Request Update')
        message = f"{status_messages.get(status, 'Your request status has been updated.')} (Patient: {patient_name}, Blood Group: {blood_group})"
        notif_type = notification_types.get(status, 'info')
        
        conn.execute('''
            INSERT INTO notifications (user_id, request_id, title, message, type, is_read)
            VALUES (?, ?, ?, ?, ?, 0)
        ''', (user_id, user_request_id, title, message, notif_type))
    
    conn.commit()
    conn.close()
    return jsonify({'id': req_id, 'status': status, 'notifications_sent': len(user_requests)})

@app.route('/api/admin/login', methods=['POST'])
def admin_login():
    data = request.get_json() or request.form
    username = data.get('username')
    password = data.get('password')
    conn = get_db()
    cur = conn.execute('SELECT * FROM admin WHERE username=? AND password=?', (username, password))
    row = cur.fetchone()
    conn.close()
    if row:
        return jsonify({'success': True})
    return jsonify({'success': False}), 401

def generate_donor_report():
    """Generate comprehensive blood request report"""
    conn = get_db()
    
    # Get all blood requests
    cur = conn.execute('SELECT * FROM requests ORDER BY created_at DESC')
    requests = [dict(row) for row in cur.fetchall()]
    
    # Get donor statistics
    cur = conn.execute('SELECT COUNT(*) as count FROM donors')
    total_donors = cur.fetchone()['count']
    
    # Get blood group statistics
    cur = conn.execute('SELECT blood_group, COUNT(*) as count FROM requests GROUP BY blood_group')
    blood_stats = {row['blood_group']: row['count'] for row in cur.fetchall()}
    
    # Get all donors for the donor information section
    cur = conn.execute('SELECT * FROM donors ORDER BY name')
    donors = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    # Create PDF buffer
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=36, leftMargin=36, topMargin=72, bottomMargin=18)
    
    # Define styles
    styles = getSampleStyleSheet()
    
    # Custom styles
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=24,
        spaceAfter=30,
        alignment=TA_CENTER,
        textColor=colors.HexColor('#dc2626')
    )
    
    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=16,
        spaceAfter=12,
        textColor=colors.HexColor('#dc2626')
    )
    
    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )
    
    # Build PDF content
    story = []
    
    # Title
    story.append(Paragraph("LifeGrid Blood Bank", title_style))
    story.append(Paragraph("Blood Request Report", title_style))
    story.append(Spacer(1, 20))
    
    # Report info
    report_date = datetime.now().strftime("%B %d, %Y at %I:%M %p")
    story.append(Paragraph(f"<b>Report Generated:</b> {report_date}", normal_style))
    story.append(Paragraph(f"<b>Total Blood Requests:</b> {len(requests)}", normal_style))
    story.append(Paragraph(f"<b>Total Registered Donors:</b> {total_donors}", normal_style))
    story.append(Spacer(1, 20))
    
    # Executive Summary
    story.append(Paragraph("Executive Summary", heading_style))
    
    # Status summary
    status_counts = {}
    for req in requests:
        status = req['status']
        status_counts[status] = status_counts.get(status, 0) + 1
    
    summary_data = [
        ['Status', 'Count', 'Percentage'],
    ]
    
    total_requests = len(requests)
    for status in ['pending', 'approved', 'fulfilled', 'rejected']:
        count = status_counts.get(status, 0)
        percentage = f"{(count/total_requests*100):.1f}%" if total_requests > 0 else "0%"
        summary_data.append([status.title(), str(count), percentage])
    
    summary_table = Table(summary_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
    summary_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(summary_table)
    story.append(Spacer(1, 20))
    
    # Blood Group Analysis
    story.append(Paragraph("Blood Group Demand Analysis", heading_style))
    
    blood_group_data = [
        ['Blood Group', 'Total Requests', 'Pending', 'Approved', 'Fulfilled', 'Rejected'],
    ]
    
    for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
        bg_requests = [r for r in requests if r['blood_group'] == bg]
        total_bg = len(bg_requests)
        pending_bg = len([r for r in bg_requests if r['status'] == 'pending'])
        approved_bg = len([r for r in bg_requests if r['status'] == 'approved'])
        fulfilled_bg = len([r for r in bg_requests if r['status'] == 'fulfilled'])
        rejected_bg = len([r for r in bg_requests if r['status'] == 'rejected'])
        
        blood_group_data.append([
            bg, str(total_bg), str(pending_bg), str(approved_bg), str(fulfilled_bg), str(rejected_bg)
        ])
    
    blood_group_table = Table(blood_group_data, colWidths=[1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch, 1.2*inch])
    blood_group_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ]))
    
    story.append(blood_group_table)
    story.append(Spacer(1, 20))
    
    # Detailed Request Information
    story.append(Paragraph("Detailed Blood Request Information", heading_style))
    
    if requests:
        # Create detailed table with all request information
        detailed_data = [
            ['ID', 'Patient Name', 'Blood Group', 'Units', 'Hospital', 'City', 'Contact', 'Status', 'Date']
        ]
        
        for req in requests:
            # Format date
            request_date = req['created_at']
            if request_date:
                try:
                    date_obj = datetime.strptime(request_date, '%Y-%m-%d %H:%M:%S')
                    formatted_date = date_obj.strftime('%d/%m/%Y')
                except:
                    formatted_date = request_date
            else:
                formatted_date = 'N/A'
            
            detailed_data.append([
                str(req['id']),
                req['patient_name'],
                req['blood_group'],
                str(req['units']) if req['units'] else 'N/A',
                req['hospital'] if req['hospital'] else 'N/A',
                req['city'] if req['city'] else 'N/A',
                req['contact'] if req['contact'] else 'N/A',
                req['status'].title(),
                formatted_date
            ])
        
        # Create table with smaller font for better fit
        detailed_table = Table(detailed_data, colWidths=[0.6*inch, 1.4*inch, 0.8*inch, 0.6*inch, 1.2*inch, 1*inch, 1.2*inch, 0.8*inch, 0.8*inch])
        detailed_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 8),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 7),
            ('VALIGN', (0, 0), (-1, -1), 'TOP')
        ]))
        
        story.append(detailed_table)
    else:
        story.append(Paragraph("No blood requests found in the system.", normal_style))
    
    story.append(Spacer(1, 20))
    
    # Donor Information Section
    story.append(Paragraph("Registered Donor Information", heading_style))
    
    # Add donor statistics summary
    story.append(Paragraph(f"<b>Total Registered Donors:</b> {len(donors)}", normal_style))
    story.append(Spacer(1, 10))
    
    if donors:
        # Create comprehensive donor table
        donor_data = [
            ['ID', 'Full Name', 'Age', 'Blood Group', 'Contact Number', 'City', 'Last Donation Date']
        ]
        
        for donor in donors:
            donor_data.append([
                str(donor['id']),
                donor['name'],
                str(donor['age']) if donor['age'] else 'N/A',
                donor['blood_group'],
                donor['contact'] if donor['contact'] else 'N/A',
                donor['city'] if donor['city'] else 'N/A',
                donor['last_donation_date'] if donor['last_donation_date'] else 'No Previous Donations'
            ])
        
        # Create donor table with improved formatting
        donor_table = Table(donor_data, colWidths=[0.6*inch, 1.6*inch, 0.6*inch, 0.8*inch, 1.2*inch, 1*inch, 1.2*inch])
        donor_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('TOPPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('TOPPADDING', (0, 1), (-1, -1), 8),
            ('BOTTOMPADDING', (0, 1), (-1, -1), 8)
        ]))
        
        story.append(donor_table)
        
        # Add donor summary by blood group
        story.append(Spacer(1, 15))
        story.append(Paragraph("Donor Distribution by Blood Group", heading_style))
        
        # Count donors by blood group
        blood_group_counts = {}
        for donor in donors:
            bg = donor['blood_group']
            blood_group_counts[bg] = blood_group_counts.get(bg, 0) + 1
        
        # Create blood group summary table
        bg_summary_data = [['Blood Group', 'Number of Donors', 'Percentage']]
        total_donors = len(donors)
        
        for bg in ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']:
            count = blood_group_counts.get(bg, 0)
            percentage = f"{(count/total_donors*100):.1f}%" if total_donors > 0 else "0%"
            bg_summary_data.append([bg, str(count), percentage])
        
        bg_summary_table = Table(bg_summary_data, colWidths=[1.5*inch, 1.5*inch, 1.5*inch])
        bg_summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#dc2626')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#fef2f2')),
            ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ('FONTSIZE', (0, 1), (-1, -1), 9)
        ]))
        
        story.append(bg_summary_table)
        
    else:
        story.append(Paragraph("No donors registered in the system.", normal_style))
    
    # Footer
    story.append(Spacer(1, 30))
    story.append(Paragraph("This report contains confidential medical information and should be handled according to healthcare privacy regulations.", normal_style))
    story.append(Paragraph("Generated by LifeGrid Blood Bank Management System", normal_style))
    
    # Build PDF
    doc.build(story)
    buffer.seek(0)
    return buffer

@app.route('/api/reports/donors', methods=['GET'])
def download_donor_report():
    """Download comprehensive blood request report as PDF"""
    try:
        pdf_buffer = generate_donor_report()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LifeGrid_Blood_Request_Report_{timestamp}.pdf"
        
        return Response(
            pdf_buffer.getvalue(),
            mimetype='application/pdf',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/pdf'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_excel_report():
    """Generate comprehensive Excel report with all data"""
    conn = get_db()
    
    # Get all data
    cur = conn.execute('SELECT * FROM donors ORDER BY name')
    donors = [dict(row) for row in cur.fetchall()]
    
    cur = conn.execute('SELECT * FROM requests ORDER BY created_at DESC')
    requests = [dict(row) for row in cur.fetchall()]
    
    conn.close()
    
    # Create Excel workbook in memory
    output = io.BytesIO()
    workbook = xlsxwriter.Workbook(output, {'in_memory': True})
    
    # Define formats
    header_format = workbook.add_format({
        'bold': True,
        'font_color': 'white',
        'bg_color': '#dc2626',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    subheader_format = workbook.add_format({
        'bold': True,
        'font_color': '#dc2626',
        'border': 1,
        'align': 'center',
        'valign': 'vcenter'
    })
    
    data_format = workbook.add_format({
        'border': 1,
        'align': 'left',
        'valign': 'vcenter'
    })
    
    number_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': '0'
    })
    
    date_format = workbook.add_format({
        'border': 1,
        'align': 'center',
        'valign': 'vcenter',
        'num_format': 'dd/mm/yyyy'
    })
    
    # Create Summary Sheet
    summary_sheet = workbook.add_worksheet('Executive Summary')
    
    # Title
    summary_sheet.merge_range('A1:H1', 'LifeGrid Blood Bank - Executive Summary', header_format)
    summary_sheet.merge_range('A2:H2', f'Report Generated: {datetime.now().strftime("%B %d, %Y at %I:%M %p")}', data_format)
    summary_sheet.merge_range('A3:H3', f'Total Donors: {len(donors)} | Total Requests: {len(requests)}', data_format)
    
    # Blood Group Statistics
    summary_sheet.write('A5', 'Blood Group Statistics', subheader_format)
    
    # Headers
    headers = ['Blood Group', 'Total Donors', 'Total Requests', 'Pending Requests', 'Approved Requests', 'Fulfilled Requests', 'Demand Ratio', 'Status']
    for col, header in enumerate(headers):
        summary_sheet.write(5, col, header, header_format)
    
    # Blood group analysis
    blood_groups = ['A+', 'A-', 'B+', 'B-', 'AB+', 'AB-', 'O+', 'O-']
    row = 6
    
    for bg in blood_groups:
        donor_count = len([d for d in donors if d['blood_group'] == bg])
        total_requests = len([r for r in requests if r['blood_group'] == bg])
        pending_requests = len([r for r in requests if r['blood_group'] == bg and r['status'] == 'pending'])
        approved_requests = len([r for r in requests if r['blood_group'] == bg and r['status'] == 'approved'])
        fulfilled_requests = len([r for r in requests if r['blood_group'] == bg and r['status'] == 'fulfilled'])
        
        ratio = f"{total_requests}/{donor_count}" if donor_count > 0 else "0/0"
        status = "High Demand" if total_requests > donor_count else "Adequate" if donor_count > 0 else "No Donors"
        
        summary_sheet.write(row, 0, bg, data_format)
        summary_sheet.write(row, 1, donor_count, number_format)
        summary_sheet.write(row, 2, total_requests, number_format)
        summary_sheet.write(row, 3, pending_requests, number_format)
        summary_sheet.write(row, 4, approved_requests, number_format)
        summary_sheet.write(row, 5, fulfilled_requests, number_format)
        summary_sheet.write(row, 6, ratio, data_format)
        summary_sheet.write(row, 7, status, data_format)
        row += 1
    
    # Set column widths
    summary_sheet.set_column('A:A', 12)
    summary_sheet.set_column('B:H', 15)
    
    # Create Donors Sheet
    donors_sheet = workbook.add_worksheet('Donor Records')
    
    # Title
    donors_sheet.merge_range('A1:H1', 'LifeGrid Blood Bank - Donor Records', header_format)
    
    # Headers
    donor_headers = ['ID', 'Full Name', 'Age', 'Blood Group', 'Contact Number', 'City', 'Last Donation Date', 'Registration Status']
    for col, header in enumerate(donor_headers):
        donors_sheet.write(2, col, header, header_format)
    
    # Donor data
    row = 3
    for donor in donors:
        donors_sheet.write(row, 0, donor['id'], number_format)
        donors_sheet.write(row, 1, donor['name'], data_format)
        donors_sheet.write(row, 2, donor['age'] if donor['age'] else 'N/A', number_format)
        donors_sheet.write(row, 3, donor['blood_group'], data_format)
        donors_sheet.write(row, 4, donor['contact'] if donor['contact'] else 'N/A', data_format)
        donors_sheet.write(row, 5, donor['city'] if donor['city'] else 'N/A', data_format)
        donors_sheet.write(row, 6, donor['last_donation_date'] if donor['last_donation_date'] else 'No Previous Donations', data_format)
        donors_sheet.write(row, 7, 'Active', data_format)
        row += 1
    
    # Set column widths
    donors_sheet.set_column('A:A', 8)
    donors_sheet.set_column('B:B', 20)
    donors_sheet.set_column('C:C', 8)
    donors_sheet.set_column('D:D', 12)
    donors_sheet.set_column('E:E', 15)
    donors_sheet.set_column('F:F', 15)
    donors_sheet.set_column('G:G', 20)
    donors_sheet.set_column('H:H', 15)
    
    # Create Requests Sheet
    requests_sheet = workbook.add_worksheet('Blood Requests')
    
    # Title
    requests_sheet.merge_range('A1:I1', 'LifeGrid Blood Bank - Blood Requests', header_format)
    
    # Headers
    request_headers = ['ID', 'Patient Name', 'Blood Group', 'Units Required', 'Hospital', 'City', 'Contact', 'Status', 'Request Date']
    for col, header in enumerate(request_headers):
        requests_sheet.write(2, col, header, header_format)
    
    # Request data
    row = 3
    for req in requests:
        requests_sheet.write(row, 0, req['id'], number_format)
        requests_sheet.write(row, 1, req['patient_name'], data_format)
        requests_sheet.write(row, 2, req['blood_group'], data_format)
        requests_sheet.write(row, 3, req['units'] if req['units'] else 'N/A', number_format)
        requests_sheet.write(row, 4, req['hospital'] if req['hospital'] else 'N/A', data_format)
        requests_sheet.write(row, 5, req['city'] if req['city'] else 'N/A', data_format)
        requests_sheet.write(row, 6, req['contact'] if req['contact'] else 'N/A', data_format)
        requests_sheet.write(row, 7, req['status'].title(), data_format)
        
        # Format date
        if req['created_at']:
            try:
                date_obj = datetime.strptime(req['created_at'], '%Y-%m-%d %H:%M:%S')
                requests_sheet.write(row, 8, date_obj, date_format)
            except:
                requests_sheet.write(row, 8, req['created_at'], data_format)
        else:
            requests_sheet.write(row, 8, 'N/A', data_format)
        row += 1
    
    # Set column widths
    requests_sheet.set_column('A:A', 8)
    requests_sheet.set_column('B:B', 20)
    requests_sheet.set_column('C:C', 12)
    requests_sheet.set_column('D:D', 12)
    requests_sheet.set_column('E:E', 20)
    requests_sheet.set_column('F:F', 15)
    requests_sheet.set_column('G:G', 15)
    requests_sheet.set_column('H:H', 12)
    requests_sheet.set_column('I:I', 18)
    
    # Create Analytics Sheet
    analytics_sheet = workbook.add_worksheet('Analytics & Insights')
    
    # Title
    analytics_sheet.merge_range('A1:D1', 'LifeGrid Blood Bank - Analytics & Insights', header_format)
    
    # Key Metrics
    analytics_sheet.write('A3', 'Key Performance Indicators', subheader_format)
    
    metrics = [
        ['Metric', 'Value', 'Description', 'Status'],
        ['Total Active Donors', len(donors), 'Registered blood donors', 'Active'],
        ['Total Blood Requests', len(requests), 'All time blood requests', 'Active'],
        ['Pending Requests', len([r for r in requests if r['status'] == 'pending']), 'Awaiting approval', 'Attention Needed'],
        ['Fulfilled Requests', len([r for r in requests if r['status'] == 'fulfilled']), 'Successfully completed', 'Excellent'],
        ['Most Requested Blood Group', max([r['blood_group'] for r in requests], key=[r['blood_group'] for r in requests].count) if requests else 'N/A', 'Highest demand blood type', 'Monitor'],
        ['Average Request Processing Time', '2-3 days', 'Typical fulfillment time', 'Good'],
        ['Donor Retention Rate', f"{len([d for d in donors if d['last_donation_date']])}/{len(donors)}" if donors else '0/0', 'Active vs registered donors', 'Monitor']
    ]
    
    for row, metric in enumerate(metrics):
        for col, value in enumerate(metric):
            if row == 0:
                analytics_sheet.write(row + 4, col, value, header_format)
            else:
                analytics_sheet.write(row + 4, col, value, data_format)
    
    # Set column widths
    analytics_sheet.set_column('A:A', 25)
    analytics_sheet.set_column('B:B', 15)
    analytics_sheet.set_column('C:C', 30)
    analytics_sheet.set_column('D:D', 15)
    
    workbook.close()
    output.seek(0)
    return output

@app.route('/api/reports/excel', methods=['GET'])
def download_excel_report():
    """Download comprehensive Excel report with all data"""
    try:
        excel_buffer = generate_excel_report()
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"LifeGrid_Complete_Report_{timestamp}.xlsx"
        
        return Response(
            excel_buffer.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={
                'Content-Disposition': f'attachment; filename="{filename}"',
                'Content-Type': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
            }
        )
    except Exception as e:
        return jsonify({'error': str(e)}), 500

# User API endpoints
@app.route('/api/users/register', methods=['POST'])
def register_user():
    """Register a new user"""
    print("=" * 50)
    print("REGISTER USER ENDPOINT CALLED")
    print("=" * 50)
    try:
        # Get data from request
        if request.is_json:
            data = request.get_json()
            print(f"Received JSON data: {data}")
        else:
            data = request.form.to_dict()
            print(f"Received form data: {data}")
        
        name = data.get('name')
        username = data.get('username')
        email = data.get('email')
        password = data.get('password')
        contact = data.get('contact')
        blood_group = data.get('blood_group', '')
        
        print(f"Extracted values - name: {name}, username: {username}, email: {email}, password: {'*' * len(password) if password else None}, contact: {contact}, blood_group: {blood_group}")
        
        # Validation
        if not name or not username or not email or not password:
            print("Validation failed: Missing required fields")
            return jsonify({'success': False, 'error': 'Name, username, email, and password are required'}), 400
        
        conn = get_db()
        print(f"Database connection established: {DB_PATH}")
        try:
            # Check if username or email already exists
            cur = conn.execute('SELECT * FROM users WHERE username=? OR email=?', (username, email))
            existing = cur.fetchone()
            if existing:
                print(f"User already exists: {dict(existing)}")
                conn.close()
                return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
            
            # Insert new user
            print("Inserting new user into database...")
            cur = conn.execute(
                'INSERT INTO users (name, username, email, password, contact, blood_group) VALUES (?, ?, ?, ?, ?, ?)',
                (name, username, email, password, contact, blood_group)
            )
            conn.commit()
            user_id = cur.lastrowid
            print(f"User inserted successfully with ID: {user_id}")
            
            # Get the created user (without password)
            cur = conn.execute('SELECT id, name, username, email, contact, blood_group, created_at FROM users WHERE id=?', (user_id,))
            row = cur.fetchone()
            if row:
                user = dict(row)
                print(f"Retrieved user: {user}")
                conn.close()
                return jsonify({'success': True, 'user': user}), 201
            else:
                print("ERROR: Could not retrieve created user")
                conn.close()
                return jsonify({'success': False, 'error': 'Failed to retrieve created user'}), 500
        except sqlite3.IntegrityError as e:
            print(f"IntegrityError: {str(e)}")
            conn.close()
            return jsonify({'success': False, 'error': 'Username or email already exists'}), 400
        except Exception as e:
            print(f"Database error in register_user: {str(e)}")
            import traceback
            traceback.print_exc()
            conn.close()
            return jsonify({'success': False, 'error': f'Database error: {str(e)}'}), 500
    except Exception as e:
        print(f"Error in register_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/login', methods=['POST'])
def user_login():
    """User login"""
    print("=" * 50)
    print("USER LOGIN ENDPOINT CALLED")
    print("=" * 50)
    try:
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        username = data.get('username')
        password = data.get('password')
        print(f"Login attempt - username: {username}, password: {'*' * len(password) if password else None}")
        
        if not username or not password:
            return jsonify({'success': False, 'error': 'Username and password are required'}), 400
        
        conn = get_db()
        # Check username or email
        cur = conn.execute('SELECT id, name, username, email, password, contact, blood_group, created_at FROM users WHERE (username=? OR email=?) AND password=?', 
                           (username, username, password))
        row = cur.fetchone()
        conn.close()
        
        if row:
            user = dict(row)
            # Remove password from response
            del user['password']
            print(f"Login successful for user: {user['username']}")
            return jsonify({'success': True, 'user': user})
        else:
            print("Login failed: Invalid credentials")
            return jsonify({'success': False, 'error': 'Invalid username/email or password'}), 401
    except Exception as e:
        print(f"Error in user_login: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['GET'])
def get_user(user_id):
    """Get user by ID"""
    conn = get_db()
    cur = conn.execute('SELECT id, name, username, email, contact, blood_group, created_at FROM users WHERE id=?', (user_id,))
    row = cur.fetchone()
    conn.close()
    
    if row:
        return jsonify(dict(row))
    else:
        return jsonify({'error': 'User not found'}), 404

@app.route('/api/users/<int:user_id>', methods=['PUT'])
def update_user(user_id):
    """Update user details"""
    print("=" * 50)
    print(f"UPDATE USER ENDPOINT CALLED for user_id: {user_id}")
    print("=" * 50)
    try:
        conn = get_db()
        if request.is_json:
            data = request.get_json()
        else:
            data = request.form.to_dict()
        
        print(f"Update data received: {data}")
        
        name = data.get('name')
        email = data.get('email')
        contact = data.get('contact') or data.get('phone')
        blood_group = data.get('blood_group')
        
        # Basic validation
        if not name or not email:
            conn.close()
            print("Validation failed: Missing name or email")
            return jsonify({'success': False, 'error': 'Name and email are required'}), 400
        
        cur = conn.execute('SELECT * FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            print(f"User not found with ID: {user_id}")
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        print(f"Current user data: {dict(row)}")
        
        # Check if email is being changed and if it already exists
        if email != row['email']:
            cur = conn.execute('SELECT * FROM users WHERE email=? AND id!=?', (email, user_id))
            if cur.fetchone():
                conn.close()
                print("Email already exists")
                return jsonify({'success': False, 'error': 'Email already exists'}), 400
        
        # Update user
        print(f"Updating user with: name={name}, email={email}, contact={contact}, blood_group={blood_group}")
        conn.execute('UPDATE users SET name=?, email=?, contact=?, blood_group=? WHERE id=?',
                     (name, email, contact, blood_group, user_id))
        conn.commit()
        print("User updated successfully")
        
        # Get updated user
        cur = conn.execute('SELECT id, name, username, email, contact, blood_group, created_at FROM users WHERE id=?', (user_id,))
        updated_row = cur.fetchone()
        if updated_row:
            updated = dict(updated_row)
            print(f"Updated user data: {updated}")
            conn.close()
            return jsonify(updated), 200
        else:
            conn.close()
            print("Failed to retrieve updated user")
            return jsonify({'success': False, 'error': 'Failed to retrieve updated user'}), 500
    except Exception as e:
        print(f"Error in update_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    """Delete user"""
    print("=" * 50)
    print(f"DELETE USER ENDPOINT CALLED for user_id: {user_id}")
    print("=" * 50)
    try:
        conn = get_db()
        cur = conn.execute('SELECT * FROM users WHERE id=?', (user_id,))
        row = cur.fetchone()
        if not row:
            conn.close()
            print(f"User not found with ID: {user_id}")
            return jsonify({'success': False, 'error': 'User not found'}), 404
        
        print(f"Deleting user: {dict(row)}")
        conn.execute('DELETE FROM users WHERE id=?', (user_id,))
        conn.commit()
        print(f"User {user_id} deleted successfully")
        conn.close()
        return jsonify({'success': True}), 200
    except Exception as e:
        print(f"Error in delete_user: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/users/<int:user_id>/donations', methods=['GET'])
def get_user_donations(user_id):
    """Get user's donation history"""
    conn = get_db()
    cur = conn.execute('''
        SELECT ud.id, ud.user_id, ud.donor_id, ud.blood_group, ud.donation_date, 
               ud.location, ud.units_donated, ud.notes, d.name as donor_name
        FROM user_donations ud
        LEFT JOIN donors d ON ud.donor_id = d.id
        WHERE ud.user_id = ?
        ORDER BY ud.donation_date DESC
    ''', (user_id,))
    donations = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify({'donations': donations})

@app.route('/api/users/<int:user_id>/donations', methods=['POST'])
def add_user_donation(user_id):
    """Add a donation to user's history"""
    conn = get_db()
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['blood_group', 'donation_date', 'location', 'units_donated']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    # Check if user exists
    cur = conn.execute('SELECT id FROM users WHERE id=?', (user_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Insert donation
    cur = conn.execute('''
        INSERT INTO user_donations (user_id, blood_group, donation_date, location, units_donated, notes)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user_id, data['blood_group'], data['donation_date'], data['location'], 
          data['units_donated'], data.get('notes', '')))
    
    donation_id = cur.lastrowid
    conn.commit()
    
    # Get the created donation
    cur = conn.execute('''
        SELECT ud.id, ud.user_id, ud.donor_id, ud.blood_group, ud.donation_date, 
               ud.location, ud.units_donated, ud.notes
        FROM user_donations ud
        WHERE ud.id = ?
    ''', (donation_id,))
    donation = dict(cur.fetchone())
    conn.close()
    
    return jsonify({'success': True, 'donation': donation}), 201

@app.route('/api/users/<int:user_id>/requests', methods=['GET'])
def get_user_requests(user_id):
    """Get user's blood request history"""
    conn = get_db()
    cur = conn.execute('''
        SELECT ur.id, ur.user_id, ur.request_id, ur.patient_name, ur.blood_group, 
               ur.units_requested, ur.hospital, ur.city, ur.contact, ur.urgency_level, 
               ur.status, ur.created_at, r.created_at as original_created_at
        FROM user_requests ur
        LEFT JOIN requests r ON ur.request_id = r.id
        WHERE ur.user_id = ?
        ORDER BY ur.created_at DESC
    ''', (user_id,))
    requests = [dict(row) for row in cur.fetchall()]
    conn.close()
    return jsonify({'requests': requests})

@app.route('/api/users/<int:user_id>/requests', methods=['POST'])
def add_user_request(user_id):
    """Add a blood request to user's history"""
    conn = get_db()
    data = request.get_json() or {}
    
    # Validate required fields
    required_fields = ['patient_name', 'blood_group', 'units_requested', 'hospital', 'city', 'contact']
    for field in required_fields:
        if not data.get(field):
            return jsonify({'success': False, 'error': f'{field} is required'}), 400
    
    # Check if user exists
    cur = conn.execute('SELECT id FROM users WHERE id=?', (user_id,))
    if not cur.fetchone():
        conn.close()
        return jsonify({'success': False, 'error': 'User not found'}), 404
    
    # Insert user request
    cur = conn.execute('''
        INSERT INTO user_requests (user_id, request_id, patient_name, blood_group, units_requested, 
                                  hospital, city, contact, urgency_level, status)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (user_id, data.get('request_id'), data['patient_name'], data['blood_group'], data['units_requested'],
          data['hospital'], data['city'], data['contact'], 
          data.get('urgency_level', 'normal'), data.get('status', 'pending')))
    
    request_id = cur.lastrowid
    conn.commit()
    
    # Get the created request
    cur = conn.execute('''
        SELECT ur.id, ur.user_id, ur.request_id, ur.patient_name, ur.blood_group, 
               ur.units_requested, ur.hospital, ur.city, ur.contact, ur.urgency_level, 
               ur.status, ur.created_at
        FROM user_requests ur
        WHERE ur.id = ?
    ''', (request_id,))
    user_request = dict(cur.fetchone())
    conn.close()
    
    return jsonify({'success': True, 'request': user_request}), 201

# Notification API endpoints
@app.route('/api/users/<int:user_id>/notifications', methods=['GET'])
def get_user_notifications(user_id):
    """Get all notifications for a user"""
    conn = get_db()
    
    # Get query parameters for filtering
    unread_only = request.args.get('unread_only', 'false').lower() == 'true'
    
    if unread_only:
        cur = conn.execute('''
            SELECT * FROM notifications 
            WHERE user_id = ? AND is_read = 0
            ORDER BY created_at DESC
        ''', (user_id,))
    else:
        cur = conn.execute('''
            SELECT * FROM notifications 
            WHERE user_id = ?
            ORDER BY created_at DESC
        ''', (user_id,))
    
    notifications = [dict(row) for row in cur.fetchall()]
    
    # Get unread count
    cur = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,))
    unread_count = cur.fetchone()['count']
    
    conn.close()
    return jsonify({
        'notifications': notifications,
        'unread_count': unread_count
    })

@app.route('/api/users/<int:user_id>/notifications/<int:notification_id>/read', methods=['PUT'])
def mark_notification_read(user_id, notification_id):
    """Mark a notification as read"""
    conn = get_db()
    
    # Verify notification belongs to user
    cur = conn.execute('SELECT * FROM notifications WHERE id = ? AND user_id = ?', (notification_id, user_id))
    notification = cur.fetchone()
    
    if not notification:
        conn.close()
        return jsonify({'success': False, 'error': 'Notification not found'}), 404
    
    # Mark as read
    conn.execute('UPDATE notifications SET is_read = 1 WHERE id = ?', (notification_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Notification marked as read'})

@app.route('/api/users/<int:user_id>/notifications/read-all', methods=['PUT'])
def mark_all_notifications_read(user_id):
    """Mark all notifications as read for a user"""
    conn = get_db()
    
    conn.execute('UPDATE notifications SET is_read = 1 WHERE user_id = ?', (user_id,))
    conn.commit()
    
    # Get updated count
    cur = conn.execute('SELECT COUNT(*) as count FROM notifications WHERE user_id = ? AND is_read = 0', (user_id,))
    unread_count = cur.fetchone()['count']
    
    conn.close()
    return jsonify({'success': True, 'message': 'All notifications marked as read', 'unread_count': unread_count})

@app.route('/api/users/<int:user_id>/notifications/<int:notification_id>', methods=['DELETE'])
def delete_notification(user_id, notification_id):
    """Delete a notification"""
    conn = get_db()
    
    # Verify notification belongs to user
    cur = conn.execute('SELECT * FROM notifications WHERE id = ? AND user_id = ?', (notification_id, user_id))
    notification = cur.fetchone()
    
    if not notification:
        conn.close()
        return jsonify({'success': False, 'error': 'Notification not found'}), 404
    
    # Delete notification
    conn.execute('DELETE FROM notifications WHERE id = ?', (notification_id,))
    conn.commit()
    conn.close()
    
    return jsonify({'success': True, 'message': 'Notification deleted'})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)


@app.route('/api/donors/<int:donor_id>', methods=['PUT'])
def update_donor(donor_id):
    """Update donor details"""
    conn = get_db()
    data = request.get_json() or {}
    name = data.get('name')
    email = data.get('email')
    phone = data.get('phone')
    blood_group = data.get('blood_group')
    # Basic validation
    if not name or not email:
        return jsonify({'success': False, 'error': 'Name and email are required'}), 400
    cur = conn.execute('SELECT * FROM donors WHERE id=?', (donor_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Donor not found'}), 404
    conn.execute('UPDATE donors SET name=?, email=?, phone=?, blood_group=? WHERE id=?',
                 (name, email, phone, blood_group, donor_id))
    conn.commit()
    cur = conn.execute('SELECT * FROM donors WHERE id=?', (donor_id,))
    updated = dict(cur.fetchone())
    return jsonify(updated), 200

@app.route('/api/donors/<int:donor_id>', methods=['DELETE'])
def delete_donor(donor_id):
    """Delete donor"""
    conn = get_db()
    cur = conn.execute('SELECT * FROM donors WHERE id=?', (donor_id,))
    row = cur.fetchone()
    if not row:
        return jsonify({'success': False, 'error': 'Donor not found'}), 404
    conn.execute('DELETE FROM donors WHERE id=?', (donor_id,))
    conn.commit()
    return jsonify({'success': True}), 200
