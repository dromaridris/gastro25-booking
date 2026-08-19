"""QR code generation checks."""

import qr_service

result = qr_service.generate_for_print('https://example.com/colonoscopy/1')
assert result.get('data_uri') or result.get('fallback_url'), 'Need data URI or fallback URL'
if result.get('data_uri'):
    assert result['data_uri'].startswith('data:image/png;base64,')
if result.get('fallback_url'):
    assert 'qrserver.com' in result['fallback_url']
print('QR service OK:', 'embedded' if result.get('data_uri') else 'fallback URL')
