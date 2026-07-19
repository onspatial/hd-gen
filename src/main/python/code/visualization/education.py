import matplotlib.pyplot as plt
import numpy as np

simulation2 = {
    'HighSchoolOrCollege': 53.75,
    'Bachelors': 23.26,
    'Graduate': 13.2,
    'Low': 9.79
}
simulation = {'HighSchoolOrCollege': 54.3, 'Bachelors': 22.8, 'Graduate': 12.4, 'Low': 10.5}
census = {
    'Low': 10.8,
    'HighSchoolOrCollege': 54.3,
    'Bachelors': 21.2,
    'Graduate': 13.7
}

categories = ['HighSchoolOrCollege', 'Bachelors', 'Graduate', 'Low']

sim_vals = [simulation[c] for c in categories]
cen_vals = [census[c] for c in categories]

y = np.arange(len(categories))
bar_height = 0.35

plt.figure(figsize=(10.5, 4.6))

plt.barh(y - bar_height/2, sim_vals, height=bar_height, label='Simulation')
plt.barh(y + bar_height/2, cen_vals, height=bar_height, label='Census')

plt.yticks(y, categories)
plt.xlabel('Percentage')
plt.title('Education Distribution')
plt.legend()
plt.gca().invert_yaxis()   # puts HighSchoolOrCollege at the top like your image
plt.tight_layout()

plt.savefig("education_distribution_both.png", dpi=300, bbox_inches="tight")
plt.close()

print("Saved to education_distribution_both.png")