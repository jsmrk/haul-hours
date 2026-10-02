from io import BytesIO
from textwrap import wrap
from zoneinfo import ZoneInfo

from reportlab.lib.pagesizes import landscape, letter
from reportlab.pdfgen.canvas import Canvas

from planner.constants import MAX_BODY_BYTES
from planner.contracts import DutyStatus, LogMetadata
from planner.errors import PlanningProblem
from planner.logs.contracts import DailyLog


def hours(seconds: int) -> str:
    return f"{seconds // 3600:02d}:{seconds % 3600 // 60:02d}:{seconds % 60:02d}"


def draw_log_pdf(logs: tuple[DailyLog, ...], metadata: LogMetadata) -> bytes:
    buffer = BytesIO()
    canvas = Canvas(buffer, pagesize=landscape(letter), pageCompression=1)
    canvas.setTitle("Haul Hours - Projected driver daily logs")
    canvas.setAuthor("Haul Hours")
    for log in logs:
        canvas.setFillColorRGB(.063, .067, .078)
        canvas.setStrokeColorRGB(.063, .067, .078)
        canvas.setFont("Helvetica-Bold", 18)
        canvas.drawString(36, 572, "Projected driver daily log")
        canvas.setFont("Helvetica", 10)
        canvas.drawString(36, 551, f"{log.date}  |  {log.timezone}  |  {hours(log.duration_s)} elapsed")
        canvas.drawRightString(756, 572, "HAUL HOURS")
        headers = [("Driver", metadata.driver_name), ("Carrier", metadata.carrier_name),
                   ("Truck / trailer", f"{metadata.truck_number or 'Not provided'} / {metadata.trailer_number or 'Not provided'}"),
                   ("Shipment", metadata.shipment_reference), ("Carrier address", metadata.carrier_address),
                   ("Starting odometer", str(metadata.starting_odometer_miles) if metadata.starting_odometer_miles is not None else None)]
        for index, (label, value) in enumerate(headers):
            x = 36 if index % 2 == 0 else 408
            y = 527 - (index // 2) * 28
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawString(x, y, label)
            canvas.setFont("Helvetica", 9)
            for line_index, line in enumerate(wrap(value or "Not provided", 62)[:2]):
                canvas.drawString(x, y - 11 - line_index * 9, line)
        left, top, width, row_height = 118, 411, 554, 29
        canvas.setFont("Helvetica-Bold", 9)
        canvas.drawString(700, top + 23, "TOTAL")
        for row, label in enumerate(("OFF DUTY", "SLEEPER", "DRIVING", "ON DUTY")):
            canvas.setFont("Helvetica-Bold", 9)
            canvas.drawRightString(left - 12, top - row * row_height - 18, label)
            canvas.setFont("Helvetica", 9)
            canvas.drawString(696, top - row * row_height - 18, hours(log.totals_s[list(DutyStatus)[row]]))
        for index in range(5):
            canvas.setLineWidth(.6)
            y = top - index * row_height
            canvas.line(left, y, left + width, y)
        for elapsed in range(0, log.duration_s + 1, 900):
            x = left + elapsed / log.duration_s * width
            canvas.setLineWidth(.45 if elapsed % 3600 == 0 else .15)
            canvas.line(x, top, x, top - 4 * row_height)
        for tick in log.graph.ticks:
            x = left + tick.elapsed_s / log.duration_s * width
            canvas.setFont("Helvetica", 6.5)
            canvas.drawCentredString(x, top + 9, tick.label.split(" ")[0][:5])
            if log.duration_s != 86400:
                canvas.setFont("Helvetica", 5.5)
                canvas.drawCentredString(x, top + 19, tick.label.split("UTC")[-1])
        canvas.setLineWidth(1.8)
        for path in log.graph.paths:
            drawing = canvas.beginPath()
            for index, (fraction, row) in enumerate(path.points):
                x, y = left + fraction * width, top - (row + .5) * row_height
                drawing.moveTo(x, y) if index == 0 else drawing.lineTo(x, y)
            canvas.drawPath(drawing)
        canvas.setFont("Helvetica-Bold", 10)
        canvas.drawString(36, 275, f"Planned miles: {log.distance_m / 1609.344:,.2f}")
        canvas.drawString(36, 253, "REMARKS / LOCATIONS")
        canvas.setFont("Helvetica", 8)
        lines = []
        for remark in log.remarks:
            stamp = remark.at.astimezone(ZoneInfo(log.timezone)).strftime("%H:%M %Z")
            lines.extend(wrap(f"{stamp} | {remark.location_label} | {remark.note}", 151))
        for index, line in enumerate(lines[:16]):
            canvas.drawString(36, 237 - index * 10, line)
        canvas.setFont("Helvetica", 8)
        canvas.drawString(36, 44, "Signature: __________________________________  (not signed)")
        canvas.drawString(408, 44, "Projection based on supplied trip assumptions.")
        canvas.showPage()
        for offset in range(16, len(lines), 46):
            canvas.setFont("Helvetica-Bold", 14)
            canvas.drawString(36, 572, f"{log.date} - Remarks continued")
            canvas.setFont("Helvetica", 9)
            for index, line in enumerate(lines[offset:offset + 46]):
                canvas.drawString(36, 545 - index * 11, line)
            canvas.showPage()
    canvas.save()
    pdf = buffer.getvalue()
    if len(pdf) > MAX_BODY_BYTES:
        raise PlanningProblem("RESULT_TOO_LARGE", "The PDF exceeds the export size limit.", 413)
    return pdf
