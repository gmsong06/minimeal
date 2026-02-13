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
    1177,  # Folate, total
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
