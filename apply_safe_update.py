from __future__ import annotations

import ast
import hashlib
import shutil
import sys
from datetime import datetime
from pathlib import Path


BASELINE_COMMIT = "e7dc8ea713767632b52c3483e8ebb0109f808b2d"
EXPECTED_BLOBS = {
    "app.py": "8fc82979af3e2d25878bc5386565e71cba280333",
    "templates/ercp_report.html": "e7f09f00dcd1daf4b24d6582019cd6c28a7fce30",
    "static/js/app.js": "917855666f66a99865bbf38e659915b5a9a461d7",
    "templates/base.html": "5f5e585be46f72f9192b0f2d520a3089f99c7128",
    "static/css/style.css": "7a8500e3971efa45ad43411833f2470aefdd37c5",
}


def git_blob_sha(text: str) -> str:
    data = text.replace("\r\n", "\n").encode("utf-8")
    return hashlib.sha1(f"blob {len(data)}\0".encode("ascii") + data).hexdigest()


def replace_once(text: str, old: str, new: str, label: str) -> str:
    count = text.count(old)
    if count != 1:
        raise RuntimeError(f"Safety check failed for {label}: expected 1 match, found {count}.")
    return text.replace(old, new, 1)


def update_app(text: str) -> str:
    text = replace_once(
        text,
        """INDICATION_OPTIONS = [
    'Choledocholithiasis', 'Biliary stricture', 'Periampullary mass',
    'Acute/chronic pancreatitis', 'Cholangitis', 'Post-cholecystectomy bile leak',
    'Ampullary lesion', 'Other',
]""",
        """INDICATION_OPTIONS = [
    'Choledocholithiasis', 'Obstructive jaundice', 'Biliary stricture',
    'Periampullary mass', 'Acute/chronic pancreatitis', 'Cholangitis',
    'Post-cholecystectomy bile leak', 'CBD injury', 'PD injury',
    'Ampullary lesion', 'Other',
]""",
        "ERCP indication options",
    )
    text = replace_once(
        text,
        """PAPILLA_LOCATION_PHRASES = {
    'Periampullary diverticulum': 'within a periampullary diverticulum',
    'Previous sphincterotomy': 'in the setting of a previous sphincterotomy',""",
        """PAPILLA_LOCATION_PHRASES = {
    'Periampullary diverticulum': 'within a periampullary diverticulum',
    'Periampullary diverticulum — Boix Type I': 'inside a periampullary diverticulum (Boix Type I)',
    'Periampullary diverticulum — Boix Type II': 'at the margin of a periampullary diverticulum (Boix Type II)',
    'Periampullary diverticulum — Boix Type III': 'near a periampullary diverticulum (Boix Type III)',
    'Previous sphincterotomy': 'in the setting of a previous sphincterotomy',""",
        "Boix narrative phrases",
    )
    text = replace_once(
        text,
        """    if is_time_locked(row) and not has_full_access(user['role']):
        return jsonify({'error': (
            'This booking can only be deleted by an Admin once the appointment day has '
            'arrived or 48 hours have passed since it was booked.'
        )}), 403
    _delete_appointment_reports(dbconn, appt_id)""",
        """    if is_time_locked(row) and not has_full_access(user['role']) and user['role'] not in CAN_OVERRIDE:
        return jsonify({'error': (
            'This booking can only be cancelled by an Admin, HOD, Consultant, or Specialist '
            'once the appointment day has arrived or 48 hours have passed since booking.'
        )}), 403
    _delete_appointment_reports(dbconn, appt_id)""",
        "appointment cancellation permission",
    )
    return text


def update_ercp_template(text: str) -> str:
    text = replace_once(
        text,
        """        <label>Indication
          <select id="f_indication">
            <option value="">— Select —</option>
            {% for opt in indication_options %}
            <option value="{{ opt }}" {{ 'selected' if report.indication == opt }}>{{ opt }}</option>
            {% endfor %}
          </select>
        </label>""",
        """        <label>Indication
          <select id="f_indication" data-saved-value="{{ report.indication or '' }}">
            <option value="">— Select —</option>
            {% for opt in indication_options %}
            {% set indication_selected = report.indication == opt or (opt in ['CBD injury', 'PD injury'] and (report.indication or '').startswith(opt ~ ' — ')) %}
            <option value="{{ opt }}" {{ 'selected' if indication_selected }}>{{ opt }}</option>
            {% endfor %}
          </select>
        </label>""",
        "classified indication selector",
    )
    text = replace_once(
        text,
        """      </div>
      <div class="form-row">
        <label>Endoscopic Papillary Shape (Haraldsson Classification)""",
        """      </div>

      <div class="form-row ercp-auto-classification" id="injuryClassificationFields" hidden>
        <label id="cbdInjuryPatternField" hidden>CBD injury pattern
          <select id="f_cbd_injury_pattern">
            <option value="">— Select observed pattern —</option>
            <option value="Strasberg Type A">Bile leak from cystic duct stump or minor duct → Type A</option>
            <option value="Strasberg Type B">Occluded aberrant right sectoral duct → Type B</option>
            <option value="Strasberg Type C">Transected, unligated aberrant right sectoral duct → Type C</option>
            <option value="Strasberg Type D">Lateral injury to a major extrahepatic bile duct → Type D</option>
            <option value="Strasberg Type E1">Transection/stricture &gt;2 cm below hepatic confluence → Type E1</option>
            <option value="Strasberg Type E2">Transection/stricture &lt;2 cm below hepatic confluence → Type E2</option>
            <option value="Strasberg Type E3">Hilar injury with confluence preserved → Type E3</option>
            <option value="Strasberg Type E4">Hilar injury with right/left ducts separated → Type E4</option>
            <option value="Strasberg Type E5">Main duct injury plus aberrant right sectoral duct injury → Type E5</option>
          </select>
        </label>
        <label id="pdInjuryPatternField" hidden>Pancreatographic pattern
          <select id="f_pd_injury_pattern">
            <option value="">— Select observed pattern —</option>
            <option value="Takishima Class 1">Normal pancreatic duct → Class 1</option>
            <option value="Takishima Class 2a">Branch-duct injury; leak contained within pancreatic parenchyma → Class 2a</option>
            <option value="Takishima Class 2b">Branch-duct injury; leak extends outside pancreatic parenchyma → Class 2b</option>
            <option value="Takishima Class 3">Main pancreatic duct injury/disruption → Class 3</option>
          </select>
        </label>
        <label>Automatic classification
          <input type="text" id="injuryClassificationResult" readonly value="" placeholder="Select the observed pattern">
        </label>
      </div>

      <div class="form-row">
        <label>Endoscopic Papillary Shape (Haraldsson Classification)""",
        "injury classification controls",
    )
    text = replace_once(
        text,
        """          <select id="f_papilla_location">
            <option value="">— Standard location —</option>
            {% for opt in papilla_location_options %}
            <option value="{{ opt }}" {{ 'selected' if report.papilla_location == opt }}>{{ opt }}</option>
            {% endfor %}
          </select>
        </label>
      </div>
      <div class="form-row">
        <label>Papillary Access""",
        """          <select id="f_papilla_location" data-saved-value="{{ report.papilla_location or '' }}">
            <option value="">— Standard location —</option>
            {% for opt in papilla_location_options %}
            {% set location_selected = report.papilla_location == opt or (opt == 'Periampullary diverticulum' and (report.papilla_location or '').startswith(opt ~ ' — ')) %}
            <option value="{{ opt }}" {{ 'selected' if location_selected }}>{{ opt }}</option>
            {% endfor %}
          </select>
        </label>
      </div>

      <div class="form-row ercp-auto-classification" id="diverticulumClassificationFields" hidden>
        <label>Papilla relationship to diverticulum
          <select id="f_diverticulum_pattern">
            <option value="">— Select observed relationship —</option>
            <option value="Boix Type I">Papilla located inside the diverticulum → Type I</option>
            <option value="Boix Type II">Papilla located at the margin of the diverticulum → Type II</option>
            <option value="Boix Type III">Papilla located near the diverticulum → Type III</option>
          </select>
        </label>
        <label>Automatic classification
          <input type="text" id="diverticulumClassificationResult" readonly value="" placeholder="Select the observed relationship">
        </label>
      </div>

      <div class="form-row">
        <label>Papillary Access""",
        "diverticulum classification controls",
    )
    text = replace_once(
        text,
        '        <div class="ercp-cholangio-category">',
        '        <div class="ercp-cholangio-category" data-category="{{ category }}">',
        "cholangiogram category marker",
    )
    text = replace_once(
        text,
        """          {% set has_stricture = (selected_findings | select('ne', 'No stricture') | list | length > 0) %}
          <div id="strictureDetailFields" {% if not has_stricture %}hidden{% endif %}>""",
        """          {% set stricture_state = namespace(has_actual=false) %}
          {% for stricture_opt in options %}
            {% if stricture_opt != 'No stricture' and stricture_opt in selected_findings %}
              {% set stricture_state.has_actual = true %}
            {% endif %}
          {% endfor %}
          <div id="strictureDetailFields" {% if not stricture_state.has_actual %}hidden{% endif %}>""",
        "initial stricture visibility",
    )
    return text


def update_app_js(text: str) -> str:
    text = replace_once(
        text,
        "  const canDelete = manage && (hasFullAccess(ME) || !locked);",
        "  const canDelete = manage && (hasFullAccess(ME) || (ME && ME.can_override) || !locked);",
        "cancel button visibility",
    )
    text = replace_once(
        text,
        """  function gatherPayload() {
    const image_captions = {};""",
        """  function classifiedIndicationValue() {
    const indication = document.getElementById('f_indication');
    if (!indication) return '';
    if (indication.value === 'CBD injury') {
      const classification = document.getElementById('f_cbd_injury_pattern')?.value || '';
      return classification ? `CBD injury — ${classification}` : 'CBD injury';
    }
    if (indication.value === 'PD injury') {
      const classification = document.getElementById('f_pd_injury_pattern')?.value || '';
      return classification ? `PD injury — ${classification}` : 'PD injury';
    }
    return indication.value;
  }

  function classifiedPapillaLocationValue() {
    const location = document.getElementById('f_papilla_location');
    if (!location) return '';
    if (location.value === 'Periampullary diverticulum') {
      const classification = document.getElementById('f_diverticulum_pattern')?.value || '';
      return classification ? `Periampullary diverticulum — ${classification}` : location.value;
    }
    return location.value;
  }

  function setupClinicalClassifiers() {
    const indication = document.getElementById('f_indication');
    const injuryWrap = document.getElementById('injuryClassificationFields');
    const cbdField = document.getElementById('cbdInjuryPatternField');
    const pdField = document.getElementById('pdInjuryPatternField');
    const cbdSelect = document.getElementById('f_cbd_injury_pattern');
    const pdSelect = document.getElementById('f_pd_injury_pattern');
    const injuryResult = document.getElementById('injuryClassificationResult');
    const papillaLocation = document.getElementById('f_papilla_location');
    const diverticulumWrap = document.getElementById('diverticulumClassificationFields');
    const diverticulumSelect = document.getElementById('f_diverticulum_pattern');
    const diverticulumResult = document.getElementById('diverticulumClassificationResult');

    if (indication && injuryWrap && cbdField && pdField && cbdSelect && pdSelect && injuryResult) {
      const saved = indication.dataset.savedValue || '';
      if (saved.startsWith('CBD injury — ')) cbdSelect.value = saved.slice('CBD injury — '.length);
      if (saved.startsWith('PD injury — ')) pdSelect.value = saved.slice('PD injury — '.length);

      const syncInjury = () => {
        const isCbd = indication.value === 'CBD injury';
        const isPd = indication.value === 'PD injury';
        injuryWrap.hidden = !(isCbd || isPd);
        cbdField.hidden = !isCbd;
        pdField.hidden = !isPd;
        injuryResult.value = isCbd ? cbdSelect.value : (isPd ? pdSelect.value : '');
      };
      indication.addEventListener('change', syncInjury);
      cbdSelect.addEventListener('change', syncInjury);
      pdSelect.addEventListener('change', syncInjury);
      syncInjury();
    }

    if (papillaLocation && diverticulumWrap && diverticulumSelect && diverticulumResult) {
      const saved = papillaLocation.dataset.savedValue || '';
      if (saved.startsWith('Periampullary diverticulum — ')) {
        diverticulumSelect.value = saved.slice('Periampullary diverticulum — '.length);
      }
      const syncDiverticulum = () => {
        const show = papillaLocation.value === 'Periampullary diverticulum';
        diverticulumWrap.hidden = !show;
        diverticulumResult.value = show ? diverticulumSelect.value : '';
      };
      papillaLocation.addEventListener('change', syncDiverticulum);
      diverticulumSelect.addEventListener('change', syncDiverticulum);
      syncDiverticulum();
    }
  }

  function gatherPayload() {
    const image_captions = {};""",
        "ERCP classifier JavaScript",
    )
    text = replace_once(
        text,
        "      indication: document.getElementById('f_indication').value,",
        "      indication: classifiedIndicationValue(),",
        "classified indication save",
    )
    text = replace_once(
        text,
        "      papilla_location: document.getElementById('f_papilla_location').value,",
        "      papilla_location: classifiedPapillaLocationValue(),",
        "classified diverticulum save",
    )
    text = replace_once(
        text,
        """    const details = document.getElementById('strictureDetailFields');
    if (!wrap || !details) return;

    function hasActualStricture() {
      return Array.from(wrap.querySelectorAll('.ercp-cholangio-toggle-opt.is-selected'))
        .some(opt => {
          const value = (opt.dataset.value || '').trim().toLowerCase();
          return value && value !== 'no stricture';
        });
    }""",
        """    const details = document.getElementById('strictureDetailFields');
    const strictureCategory = wrap?.querySelector('[data-category="Strictures"]');
    if (!wrap || !details || !strictureCategory) return;

    function hasActualStricture() {
      return Array.from(strictureCategory.querySelectorAll('.ercp-cholangio-toggle-opt.is-selected'))
        .some(opt => (opt.dataset.value || '').trim().toLowerCase() !== 'no stricture');
    }""",
        "live stricture visibility",
    )
    text = replace_once(
        text,
        """        numericFields.forEach(f => { f.value = ''; });
        updateDilatationBadge();""",
        """        numericFields.forEach(f => { f.value = ''; });
        wrap.dispatchEvent(new CustomEvent('cholangio-toggle', { bubbles: true }));
        updateDilatationBadge();""",
        "stricture visibility after normal reset",
    )
    text = replace_once(
        text,
        """    setupCholangioToggleLists('f_cholangiogram_findings');
    setupStrictureDetailsToggle();""",
        """    setupClinicalClassifiers();
    setupCholangioToggleLists('f_cholangiogram_findings');
    setupStrictureDetailsToggle();""",
        "classifier initialization",
    )
    return text


def update_base(text: str) -> str:
    text = replace_once(
        text,
        """    <div class="userbox">
      <span class="userbox-name">{{ current_user.full_name }}</span>""",
        """    <div class="userbox">
      <div class="ui-text-controls" aria-label="Screen text controls">
        <button type="button" class="ui-text-btn" id="uiTextDecrease" title="Decrease screen text size">A−</button>
        <span class="ui-text-value" id="uiTextValue">100%</span>
        <button type="button" class="ui-text-btn" id="uiTextIncrease" title="Increase screen text size">A+</button>
        <button type="button" class="ui-text-btn ui-text-bold-btn" id="uiTextBold" aria-pressed="false" title="Toggle bold screen text">B</button>
      </div>
      <span class="userbox-name">{{ current_user.full_name }}</span>""",
        "screen text control toolbar",
    )
    text = replace_once(
        text,
        """{% if current_user %}
<script src="{{ url_for('static', filename='js/user_mentions.js') }}"></script>
{% endif %}""",
        """{% if current_user %}
<script src="{{ url_for('static', filename='js/user_mentions.js') }}"></script>
<script>
(() => {
  const decrease = document.getElementById('uiTextDecrease');
  const increase = document.getElementById('uiTextIncrease');
  const boldButton = document.getElementById('uiTextBold');
  const value = document.getElementById('uiTextValue');
  if (!decrease || !increase || !boldButton || !value) return;

  const allowedScales = [0.9, 1, 1.1, 1.2];
  let scale = 1;
  let bold = false;
  try {
    const savedScale = Number(localStorage.getItem('gastroUiTextScale'));
    if (allowedScales.includes(savedScale)) scale = savedScale;
    bold = localStorage.getItem('gastroUiTextBold') === 'true';
  } catch (_) { /* controls remain available without storage */ }

  const apply = () => {
    document.body.style.setProperty('--ui-content-scale', String(scale));
    document.body.classList.toggle('ui-text-bold', bold);
    value.textContent = `${Math.round(scale * 100)}%`;
    decrease.disabled = scale === allowedScales[0];
    increase.disabled = scale === allowedScales[allowedScales.length - 1];
    boldButton.setAttribute('aria-pressed', bold ? 'true' : 'false');
    try {
      localStorage.setItem('gastroUiTextScale', String(scale));
      localStorage.setItem('gastroUiTextBold', String(bold));
    } catch (_) { /* no-op */ }
  };

  decrease.addEventListener('click', () => {
    scale = allowedScales[Math.max(0, allowedScales.indexOf(scale) - 1)];
    apply();
  });
  increase.addEventListener('click', () => {
    scale = allowedScales[Math.min(allowedScales.length - 1, allowedScales.indexOf(scale) + 1)];
    apply();
  });
  boldButton.addEventListener('click', () => { bold = !bold; apply(); });
  apply();
})();
</script>
{% endif %}""",
        "screen text control JavaScript",
    )
    return text


def update_css(text: str) -> str:
    return text + """

/* Screen-only text accessibility controls. Printing always uses the approved layout. */
.ui-text-controls{
  display:flex;
  align-items:center;
  gap:3px;
  margin-right:6px;
}
.ui-text-btn{
  min-width:28px;
  height:28px;
  padding:2px 6px;
  border:1px solid var(--line);
  border-radius:6px;
  background:var(--paper-raised);
  color:var(--ink);
  font:600 12px/1 var(--font-ui);
  cursor:pointer;
}
.ui-text-btn:hover{ border-color:var(--crimson); color:var(--crimson); }
.ui-text-btn:disabled{ opacity:.45; cursor:not-allowed; }
.ui-text-bold-btn{ font-weight:800; }
.ui-text-bold-btn[aria-pressed="true"]{
  color:#fff;
  background:var(--crimson);
  border-color:var(--crimson);
}
.ui-text-value{
  min-width:38px;
  text-align:center;
  font-size:11px;
  color:var(--muted);
}
@media screen{
  body .page{ zoom:var(--ui-content-scale, 1); }
  body.ui-text-bold .page,
  body.ui-text-bold .page input,
  body.ui-text-bold .page select,
  body.ui-text-bold .page textarea{ font-weight:600; }
}
@media (max-width: 760px){
  .ui-text-controls{ margin:4px 0; }
}
@media print{
  body .page{ zoom:1 !important; }
  body.ui-text-bold .page,
  body.ui-text-bold .page input,
  body.ui-text-bold .page select,
  body.ui-text-bold .page textarea{ font-weight:inherit !important; }
}
"""


UPDATERS = {
    "app.py": update_app,
    "templates/ercp_report.html": update_ercp_template,
    "static/js/app.js": update_app_js,
    "templates/base.html": update_base,
    "static/css/style.css": update_css,
}


def main() -> int:
    root = Path.cwd()
    missing = [path for path in EXPECTED_BLOBS if not (root / path).is_file()]
    if missing:
        print("ERROR: Run this script from the gastro_booking project folder.")
        print("Missing:", ", ".join(missing))
        return 1

    originals: dict[str, str] = {}
    for relative, expected in EXPECTED_BLOBS.items():
        text = (root / relative).read_text(encoding="utf-8")
        actual = git_blob_sha(text)
        if actual != expected:
            print(f"ERROR: {relative} is not the approved {BASELINE_COMMIT} version.")
            print(f"Expected {expected}; found {actual}.")
            print("Run: git sync")
            print("Then run this updater again. Nothing was changed.")
            return 1
        originals[relative] = text

    try:
        updated = {path: UPDATERS[path](text) for path, text in originals.items()}
        ast.parse(updated["app.py"])
        required = (
            "Obstructive jaundice",
            "Strasberg Type E5",
            "Takishima Class 3",
            "Boix Type III",
            '[data-category="Strictures"]',
            "uiTextBold",
            "@media print",
        )
        combined = "\n".join(updated.values())
        absent = [item for item in required if item not in combined]
        if absent:
            raise RuntimeError("Post-update validation failed: " + ", ".join(absent))
    except Exception as exc:
        print(f"ERROR: {exc}")
        print("Nothing was changed.")
        return 1

    stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Keep the safety copy outside the Git repository so `git add -A` / `git sync`
    # can never upload local runtime data or the backup itself.
    backup_root = root.parent / "gastro_booking_code_backups" / f"before_ercp_safe_update_{stamp}"
    for relative in EXPECTED_BLOBS:
        source = root / relative
        destination = backup_root / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, destination)

    for relative, text in updated.items():
        (root / relative).write_text(text, encoding="utf-8")

    print("SUCCESS: the five scoped files were updated.")
    print(f"Backup: {backup_root}")
    print("Next run:")
    print("  python -m pytest -q")
    print("  git diff --check")
    print("  git sync")
    return 0


if __name__ == "__main__":
    sys.exit(main())
