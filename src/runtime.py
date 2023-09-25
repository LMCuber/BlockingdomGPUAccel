# inkomen
tot_salary = 70_000
# de stelsel waar we kunnen aflezen hoeveel de bracket waard is
stelsel = {
    15_000: 0,  # %
    35_000: 35,  # %
    float("inf"): 40,  # %
}
# de taxatie begint op 0, en de laatste bracket is ook 0
tax = 0
last_bracket = 0
for bracket, perc in stelsel.items():
    # de belasting wordt berekend afhankelijk van de percentage; min is nodig om niet over de grens te gaan
    tax += (min(bracket, tot_salary) - last_bracket) * (perc / 100)
    # laatste bracket wordt opgeslagen zodat het kan worden afgetrokken van de volgende
    last_bracket = bracket
print(tax)

  


# totaalInkomen = 70_000
# b1 = 0
# b2 = 0.35
# b3 = 0.4
# m1 = 15000
# m2 = 35000
# bb1 = min(totaalInkomen, m1) * b1
# bb2 = (min(totaalInkomen, m2) - m1) * b2
# print(totaalInkomen, m2, m1, b2)
# bb3 = (totaalInkomen - m2) * b3
# t = max(bb3, 0) + bb2 + bb1
# print(t)
