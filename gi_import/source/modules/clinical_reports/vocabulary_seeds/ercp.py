"""ERCP vocabulary seed data — template-specific clinical terminology."""

ERCP_VOCABULARY_SEED = {
    "ercp_indication_category": [
        ("choledocholithiasis", "Choledocholithiasis / CBD stones", 10),
        ("biliary_stricture", "Biliary stricture", 20),
        ("malignant_obstruction", "Malignant biliary obstruction", 30),
        ("post_surgical_anatomy", "Post-surgical biliary anatomy", 40),
        ("sod", "Suspected sphincter of Oddi dysfunction", 50),
        ("pancreatic_disease", "Pancreatic duct disease", 60),
        ("other", "Other / specify in detail", 99),
    ],
    "ercp_urgency": [
        ("elective", "Elective", 10),
        ("urgent", "Urgent (< 72 hours)", 20),
        ("emergency", "Emergency", 30),
    ],
    "cannulation_method": [
        ("standard", "Standard wire-guided", 10),
        ("precut", "Precut sphincterotomy", 20),
        ("double_wire", "Double-wire technique", 30),
        ("transpancreatic", "Transpancreatic sphincterotomy", 40),
    ],
    "pep_prophylaxis": [
        ("rectal_indomethacin", "Rectal indomethacin", 10),
        ("pancreatic_stent", "Prophylactic pancreatic duct stent", 20),
        ("aggressive_hydration", "Aggressive IV hydration", 30),
        ("none", "None documented", 99),
    ],
    "stone_burden": [
        ("none", "None", 10),
        ("small", "Small", 20),
        ("moderate", "Moderate", 30),
        ("large", "Large / multiple", 40),
    ],
    "intervention_type": [
        ("sphincterotomy", "Biliary sphincterotomy", 10),
        ("stone_extraction", "Stone extraction", 20),
        ("balloon_dilation", "Balloon dilation", 30),
        ("biliary_stent", "Biliary stent placement", 40),
        ("pancreatic_stent", "Pancreatic duct stent", 50),
        ("brush_cytology", "Brush cytology", 60),
    ],
    "complication_type": [
        ("bleeding", "Bleeding", 10),
        ("perforation", "Perforation", 20),
        ("pancreatitis", "Pancreatitis", 30),
        ("cholangitis", "Cholangitis", 40),
        ("other", "Other", 99),
    ],
}
