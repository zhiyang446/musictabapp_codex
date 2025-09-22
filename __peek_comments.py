from pathlib import Path
import sys
text = Path('backend/app/api/v1/endpoints/jobs.py').read_text(encoding='utf-8')
start = text.index('    last_event_uuid')
sys.stdout.buffer.write(text[start:start+200].encode('utf-8'))
