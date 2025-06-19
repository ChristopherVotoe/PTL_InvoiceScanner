import smtplib
import ssl
from email.message import EmailMessage
from email.utils import make_msgid, formatdate


def send_email(pdf_path, sender_email, sender_pw, receiver_email,logo_path):
    msg = EmailMessage()
    msg['Subject'] = 'Invoices from PrimeTime'
    msg['From'] = sender_email
    msg['To'] = receiver_email
    msg['Message-ID'] = make_msgid()
    msg['Date'] = formatdate(localtime=True)

    # Generate a content ID for the logo
    logo_cid = make_msgid(domain="primetimeservice123.com")[1:-1]  # Remove < >

    # Set HTML content with embedded logo
    html_content = f"""
       <html>
           <body>
               <p>Hello,<br><br>
               Please find your invoice attached.<br><br>
               Best regards,<br>
               <strong>Primetime Logistic Services</strong>
               </p>
               <img src="cid:{logo_cid}" alt="Company Logo" style="height:80px; margin-top:20px;">
           </body>
       </html>
       """
    msg.set_content("Please find your invoice attached.")
    msg.add_alternative(html_content, subtype='html')

    # Attach the logo as an inline image
    with open(logo_path, 'rb') as img:
        msg.get_payload()[1].add_related(img.read(), 'image', 'png', cid=f"<{logo_cid}>")

    with open(pdf_path,'rb') as tmp:
        file_data = tmp.read()
        file_name = pdf_path.split('/')[-1]
    msg.add_attachment(file_data, maintype="application", subtype="pdf", filename=file_name)

    server = 'mail.primetimeservice123.com'
    port = 465
    context = ssl.create_default_context()

    with smtplib.SMTP_SSL(server,port,context=context) as server:
        server.login(sender_email,sender_pw)
        server.send_message(msg)
        print(f"Email sent to {receiver_email} with {file_name}")

# import os
# print(os.getcwd())

send_email(r"separated_invoices/JAX-922278/JAX-922278.pdf", "russell@primetimeservice123.com", "", "Chris.Votoe.Official@gmail.com",r"assets/company_logo.jpg")
