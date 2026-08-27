"""Named constants for the nutrition calculation, each with its source."""

# Mifflin-St Jeor equation (1990).
# https://www.promealplan.com/en/blog/mifflin-st-jeor-equation-coaches-guide
MIFFLIN_WEIGHT_COEF = 10.0    # per kg
MIFFLIN_HEIGHT_COEF = 6.25    # per cm
MIFFLIN_AGE_COEF = 5.0        # per year, subtracted

# Biological sex isn't collected; average of the male (+5) and female (-161) terms.
MIFFLIN_SEX_NEUTRAL_CONSTANT = -78.0

# Sedentary NEAT multiplier on BMR.
SEDENTARY_ACTIVITY_FACTOR = 1.2

# kcal/min = (MET x 3.5 x weight_kg) / 200.
# https://howdyhealth.tamu.edu/use-metabolic-equivalents-mets-to-calculate-calories-burned/
KCAL_PER_MINUTE_MET_COEF = 3.5
KCAL_PER_MINUTE_DIVISOR = 200.0

# Daily target = TDEE + goal adjustment.
# https://www.mayoclinic.org/healthy-lifestyle/weight-loss/in-depth/calories/art-20048065
WEIGHT_LOSS_DEFICIT_KCAL = 500.0
MAINTENANCE_ADJUSTMENT_KCAL = 0.0

# https://builtwithscience.com/tdee-calculator/
MUSCLE_GAIN_SURPLUS_KCAL = 300.0

# Minimum safe daily calories without medical supervision.
# https://www.mayoclinic.org/healthy-lifestyle/weight-loss/in-depth/calories/art-20048065
CALORIE_FLOOR_KCAL = 1200.0

# Deficit capped at this fraction of TDEE for low-expenditure profiles.
MAX_DEFICIT_FRACTION_OF_TDEE = 0.25
