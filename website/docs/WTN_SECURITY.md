# WTN Signature Security Implementation

## Overview
This document details the security measures implemented for Waste Transfer Notice (WTN) digital signatures to comply with UK environmental regulations and data protection requirements.

## Security Features Implemented

### 1. **Secure Storage** ✅
- **Storage**: WTN signatures are stored securely during the approval process
- **Location**: Database fields in `IncomingParcel` model
- **Access Control**: Admin-only access through Django admin interface

### 2. **PDF Generation** ✅
- **Technology**: ReportLab PDF generation
- **Implementation**: `store/wtn_pdf.py`
- **Storage**: PDFs stored in business-specific folders under `media/wtn_pdfs/`
- **Result**: Signatures are embedded in the final PDF document

### 3. **Audit Logging** ✅
- **Log File**: `website/logs/security_audit.log`
- **Events Logged**:
  - Admin signature access
  - PDF generation events
  - Any errors during PDF generation
- **Log Format**: `{levelname} {asctime} {module} {message}`

### 4. **HTTPS Enforcement** ✅
- **Production Settings** (`DEBUG=False`):
  - `SECURE_SSL_REDIRECT = True` - Force HTTPS
  - `SESSION_COOKIE_SECURE = True` - Cookies only sent over HTTPS
  - `CSRF_COOKIE_SECURE = True` - CSRF tokens only over HTTPS
  - `SECURE_HSTS_SECONDS = 31536000` - 1 year HSTS
  - `SECURE_HSTS_INCLUDE_SUBDOMAINS = True` - Apply to all subdomains
  - `SECURE_HSTS_PRELOAD = True` - Enable HSTS preloading

### 5. **PDF Storage Security**
- **Location**: `/media/wtn_pdfs/{user_id}_{business_name}/`
- **Filename Format**: `DD_MM_YYYY_WTN.pdf`
- **Access Control**: 
  - Business-specific folders prevent cross-user access
  - Django media file serving (authenticated users only in production)
- **Future Enhancement**: Consider moving to AWS S3 with server-side encryption

## Data Flow

### Customer Signs WTN:
1. Customer draws signature on canvas (customer-facing form)
2. Signature converted to base64 PNG
3. **Encrypted** signature saved to `wtn_signature` field
4. PDF **NOT** generated yet

### Admin Countersigns WTN:
1. Admin draws signature on canvas (admin panel)
2. Signature converted to base64 PNG
3. **Encrypted** signature saved to `wtn_admin_signature` field
4. Admin checks "Wtn admin approved" checkbox
5. On save:
   - PDF generated with **both signatures** embedded
   - PDF saved to `/media/wtn_pdfs/`
   - **Both signatures deleted from database**
   - Audit log entry created
   - Success message shown to admin

### PDF Access:
1. Signatures now exist **only in PDF**
2. PDF path stored in `wtn_pdf_path` field (no sensitive data)
3. Access controlled by Django authentication
4. Every access logged in audit log

## Compliance

### UK Environmental Protection Act 1990
- ✅ Digital signatures legally binding
- ✅ Waste Transfer Notice fully traceable
- ✅ Customer and admin signatures both captured
- ✅ Date and reference number recorded
- ✅ PDF provides permanent record

### GDPR (Data Protection Act 2018)
- ✅ Signatures encrypted at rest
- ✅ Minimal data retention (deleted after PDF)
- ✅ Access logging and audit trail
- ✅ Secure transmission (HTTPS only)
- ✅ Purpose limitation (only used for WTN)

## Environment Variables Required

Add to your `.env` file:
```bash
# Encryption key for signatures (KEEP SECRET!)
FERNET_KEY=V3wquydb5L3Cm03abfEe3N-AVHkrfXLJAszO-IFCb8I=

# Django settings
SECRET_KEY=your-django-secret-key
DEBUG=False  # In production

# HTTPS enforcement (automatic in production)
```

## Security Best Practices

### ✅ Implemented
- Encryption at rest
- Automatic signature deletion
- Audit logging
- HTTPS enforcement
- Session security
- CSRF protection

### 🔄 Recommended for Production
- [ ] Move PDFs to AWS S3 with server-side encryption (SSE-S3 or SSE-KMS)
- [ ] Implement PDF watermarking with timestamp
- [ ] Add rate limiting to prevent abuse
- [ ] Set up automated log monitoring/alerts
- [ ] Regular security audits
- [ ] Backup encryption keys securely (separate from codebase)

### ⚠️ Important Notes
1. **Never commit `.env` to git** - encryption keys must stay secret
2. **Backup `FERNET_KEY`** - if lost, encrypted data cannot be recovered
3. **Rotate keys annually** - plan for key rotation strategy
4. **Monitor audit logs** - review regularly for suspicious access
5. **Test PDF generation** - ensure signatures properly embedded before deletion

## Incident Response

If signatures are compromised:
1. Check `logs/security_audit.log` for unauthorized access
2. Verify PDFs are intact and accessible
3. Rotate `FERNET_KEY` immediately
4. Notify affected customers if required by GDPR
5. Review Django admin access logs

## Migration Notes

When migrating from old system:
1. Existing signatures will be encrypted on first access
2. Legacy PDFs (if any) remain unchanged
3. New WTNs automatically use encrypted workflow
4. No data loss during encryption migration

## Testing Checklist

Before deploying to production:
- [ ] Test signature encryption/decryption
- [ ] Verify PDF contains both signatures
- [ ] Confirm signatures deleted from database after PDF
- [ ] Check audit log entries created
- [ ] Test HTTPS redirect in production
- [ ] Verify PDF downloads work
- [ ] Test with empty/missing signatures (error handling)

## Support

For security issues or questions:
- Review audit logs: `/website/logs/security_audit.log`
- Check Django admin for WTN status
- Verify encryption key is set correctly
- Ensure HTTPS is working in production
