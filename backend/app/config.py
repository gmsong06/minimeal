# FDA Daily Values mapped to USDA Nutrient IDs
# Units match USDA units exactly

FDA_DAILY_VALUES = {

    # FAT-SOLUBLE VITAMINS

    1106: 900,     # Vitamin A (RAE), mcg
    1114: 20,      # Vitamin D, mcg
    1109: 15,      # Vitamin E (alpha-tocopherol), mg
    1185: 120,     # Vitamin K, mcg


    # WATER-SOLUBLE VITAMINS

    1162: 90,      # Vitamin C, mg
    1165: 1.2,     # Thiamin (B1), mg
    1166: 1.3,     # Riboflavin (B2), mg
    1167: 16,      # Niacin (B3), mg
    1170: 5,       # Pantothenic acid (B5), mg
    1175: 1.7,     # Vitamin B6, mg
    1190: 400,     # Folate, mcg DFE
    1178: 2.4,     # Vitamin B12, mcg
    1180: 550,     # Choline, mg


    # MINERALS

    1087: 1300,    # Calcium, mg
    1089: 18,      # Iron, mg
    1090: 420,     # Magnesium, mg
    1091: 1250,    # Phosphorus, mg
    1092: 4700,    # Potassium, mg
    1093: 2300,    # Sodium, mg
    1095: 11,      # Zinc, mg
    1098: 0.9,     # Copper, mg
    1101: 2.3,     # Manganese, mg
    1103: 55,      # Selenium, mcg
    1094: 150,     # Iodine, mcg


    # FIBER

    1079: 28,      # Dietary Fiber, g
}

PORTION_CLASS_GRAMS = {
    "primary_protein":      {"default": 160, "min": 120, "max": 220},
    "secondary_protein":    {"default":  65, "min":  40, "max":  90},

    "primary_starch":       {"default": 225, "min": 150, "max": 300},
    "secondary_starch":     {"default": 100, "min":  50, "max": 150},

    "primary_veg":          {"default": 150, "min": 100, "max": 220},
    "secondary_veg":        {"default":  70, "min":  40, "max": 110},

    "legume_component":     {"default": 105, "min":  60, "max": 160},

    "dairy_component":      {"default":  90, "min":  30, "max": 150},

    "sauce_condiment":      {"default":  15, "min":   5, "max":  30},
    "added_fat":            {"default":  10, "min":   5, "max":  20},
    "garnish_trace":        {"default":   2, "min":   1, "max":   5},

    "snack_item_single":    {"default":  40, "min":  25, "max":  80},
    "snack_handful":        {"default":  35, "min":  20, "max":  55},

    "beverage_caloric":     {"default": 350, "min": 240, "max": 500},
    "beverage_noncaloric":  {"default": 350, "min": 240, "max": 700},

    "other":                {"default":  65, "min":  30, "max": 120},
}

DV_TO_DAY_STATUS = [
    (100, "met"),
    (75, "strong"),
    (40, "building"),
    (20, "low"),
    (0, "none"),
]

DV_TO_LIMIT_STATUS = [
    (100, "high"),
    (75, "elevated"),
    (40, "moderate"),
    (20, "low"),
    (0, "minimal"),
]

DV_TO_MEAL_CONTRIBUTION = [
    (20, "very_significant"),
    (10, "significant"),
    (5,  "moderate"),
    (2,  "minor"),
    (0,  "negligible"),
]


# USDA Nutrient IDs (Foundation Foods)
VITAMIN_IDS = {
    # Fat-soluble
    1106,  # Vitamin A, RAE
    1114,  # Vitamin D (D2 + D3)
    1109,  # Vitamin E (alpha-tocopherol)
    1185,  # Vitamin K (phylloquinone)

    # Water-soluble
    1162,  # Vitamin C
    1165,  # Thiamin (B1)
    1166,  # Riboflavin (B2)
    1167,  # Niacin (B3)
    1170,  # Pantothenic acid (B5)
    1175,  # Vitamin B-6
    1190,  # Folate, DFE
    1178,  # Vitamin B-12
    1180,  # Choline, total
}

MINERAL_IDS = {
    1087,  # Calcium
    1089,  # Iron
    1090,  # Magnesium
    1091,  # Phosphorus
    1092,  # Potassium
    1093,  # Sodium
    1095,  # Zinc
    1098,  # Copper
    1101,  # Manganese
    1103,  # Selenium
    1094,  # Iodine
}

FIBER_IDS = {
    1079,  # Fiber, total dietary
}

ESSENTIAL_IDS = VITAMIN_IDS | MINERAL_IDS | FIBER_IDS

# Nutrients that should be interpreted as "less is better" against a daily cap.
LIMITED_NUTRIENT_IDS = {
    1093,  # Sodium
}

FOLIC_ACID_ID = 1186
FOLATE_TOTAL_ID = 1177
FOLATE_FOOD_ID = 1187
FOLATE_DFE_ID = 1190

# USDA Nutrient ID → Canonical Name (Foundation Foods)

NUTRIENT_ID_TO_NAME = {
    # VITAMINS
    1106: "Vitamin A (RAE)",
    1114: "Vitamin D",
    1109: "Vitamin E (alpha-tocopherol)",
    1185: "Vitamin K",

    1162: "Vitamin C",
    1165: "Thiamin (B1)",
    1166: "Riboflavin (B2)",
    1167: "Niacin (B3)",
    1170: "Pantothenic acid (B5)",
    1175: "Vitamin B6",
    1190: "Folate",
    1177: "Folate",
    1178: "Vitamin B12",
    1180: "Choline",

    # MINERALS
    1087: "Calcium",
    1089: "Iron",
    1090: "Magnesium",
    1091: "Phosphorus",
    1092: "Potassium",
    1093: "Sodium",
    1095: "Zinc",
    1098: "Copper",
    1101: "Manganese",
    1103: "Selenium",
    1094: "Iodine",

    # FIBER
    1079: "Dietary Fiber",
}
