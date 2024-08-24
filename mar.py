

with open("mar.txt", "r") as f, open("out.txt", "w") as g:
    for line in f.readlines():
        if ":" in line:
            time = line.split(" ")[0]
            rest = " ".join(line.split(" ")[1:])
            hours, mins = time.split(":")
            new_hours = int(hours) + 2
            new_time = f"{new_hours}:{mins}"
            new_line = f"{new_time} {rest}"
            g.write(new_line)
        else:
            g.write(line)