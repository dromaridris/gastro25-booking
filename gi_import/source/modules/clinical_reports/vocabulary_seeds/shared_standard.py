"""Shared vocabulary seeds for Standard Endoscopy structured templates."""

SHARED_STANDARD_VOCABULARY_SEED = {
    "procedure_urgency": [
        ("elective", "Elective", 10),
        ("urgent", "Urgent (< 72 hours)", 20),
        ("emergency", "Emergency", 30),
    ],
    "anticoagulation_status": [
        ("none", "None", 10),
        ("antiplatelet", "Antiplatelet therapy", 20),
        ("anticoagulant", "Anticoagulant therapy", 30),
        ("both", "Antiplatelet and anticoagulant", 40),
    ],
    "anticoagulation_management": [
        ("continued", "Continued", 10),
        ("held", "Held per protocol", 20),
        ("bridged", "Bridged", 30),
        ("not_applicable", "Not applicable", 99),
    ],
    "asa_class": [
        ("I", "ASA I", 10),
        ("II", "ASA II", 20),
        ("III", "ASA III", 30),
        ("IV", "ASA IV", 40),
        ("V", "ASA V", 50),
    ],
    "sedation_type": [
        ("local_spray", "Local pharyngeal spray", 10),
        ("midazolam", "Midazolam", 20),
        ("propofol", "Propofol", 30),
        ("fentanyl", "Fentanyl", 40),
        ("general_anaesthesia", "General anaesthesia", 50),
    ],
    "standard_complication_type": [
        ("bleeding", "Bleeding", 10),
        ("perforation", "Perforation", 20),
        ("aspiration", "Aspiration", 30),
        ("cardiorespiratory", "Cardiorespiratory event", 40),
        ("other", "Other", 99),
    ],
    "surveillance_interval": [
        ("none", "None required", 10),
        ("3_months", "3 months", 20),
        ("6_months", "6 months", 30),
        ("1_year", "1 year", 40),
        ("3_years", "3 years", 50),
        ("5_years", "5 years", 60),
        ("histology_pending", "Pending histology", 70),
    ],
    "follow_up_procedure": [
        ("none", "None", 10),
        ("repeat_ogd", "Repeat OGD", 20),
        ("repeat_colonoscopy", "Repeat colonoscopy", 30),
        ("h_pylori_test", "H. pylori testing", 40),
        ("other", "Other — see plan", 99),
    ],
}
