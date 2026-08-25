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
