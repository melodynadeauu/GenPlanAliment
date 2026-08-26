"""Named constants for the nutrition calculation, each with its source.

Every number used by the calculation lives here so it can be found, cited
and changed in one place.
"""

# Mifflin-St Jeor equation (1990), the clinically validated BMR estimate.
# Source: https://www.promealplan.com/en/blog/mifflin-st-jeor-equation-coaches-guide
MIFFLIN_WEIGHT_COEF = 10.0    # per kg
MIFFLIN_HEIGHT_COEF = 6.25    # per cm
MIFFLIN_AGE_COEF = 5.0        # per year, subtracted

# Mifflin-St Jeor's last term depends on biological sex: +5 for men,
# -161 for women. Biological sex is deliberately not collected (sensitive
# health data, data minimisation), so we use the average of both constants.
MIFFLIN_SEX_NEUTRAL_CONSTANT = -78.0

# Sedentary energy base: NEAT (non-exercise activity thermogenesis) outside
# of any structured exercise, applied as a flat multiplier on BMR.
SEDENTARY_ACTIVITY_FACTOR = 1.2

# MET-based calories-per-minute formula: kcal/min = (MET x 3.5 x weight_kg) / 200.
# Source: https://howdyhealth.tamu.edu/use-metabolic-equivalents-mets-to-calculate-calories-burned/
KCAL_PER_MINUTE_MET_COEF = 3.5
KCAL_PER_MINUTE_DIVISOR = 200.0

# Daily calorie target = TDEE + the adjustment for the user's goal. Each
# value is a single number, kept here so it can be found and changed alone.
#
# WEIGHT_LOSS: fixed daily deficit. Source (Mayo Clinic):
# https://www.mayoclinic.org/healthy-lifestyle/weight-loss/in-depth/calories/art-20048065
WEIGHT_LOSS_DEFICIT_KCAL = 500.0

# MAINTENANCE: no adjustment - the target is the TDEE itself.
MAINTENANCE_ADJUSTMENT_KCAL = 0.0

# MUSCLE_GAIN: fixed daily surplus. Source (Built With Science):
# https://builtwithscience.com/tdee-calculator/
MUSCLE_GAIN_SURPLUS_KCAL = 300.0

# G1 (Dossier de défense, section 05) : plancher calorique absolu, jamais franchi
# quel que soit le déficit calculé. 1200 kcal/jour est le seuil minimal généralement
# cité pour un adulte avant qu'une restriction ne soit considérée dangereuse sans
# supervision médicale.
# Source: https://www.mayoclinic.org/healthy-lifestyle/weight-loss/in-depth/calories/art-20048065
CALORIE_FLOOR_KCAL = 1200.0

# Second plafond sur le déficit : jamais plus de 25% du TDEE, pour les profils à
# faible dépense où un déficit fixe de 500 kcal serait disproportionné.
MAX_DEFICIT_FRACTION_OF_TDEE = 0.25
