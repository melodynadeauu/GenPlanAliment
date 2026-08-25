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

# Deliberately NOT defined here: the classic sedentary/light/moderate/active
# activity-level multipliers (1.375 / 1.55 / 1.725) used by generic TDEE
# calculators. They describe a weekly average and would make the per-day
# activity_calendar table pointless - this app computes exercise expenditure
# per scheduled activity instead.
