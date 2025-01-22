cd /root/projects/English-Learning-Material-Generator/
source .venv/bin/activate
set -o allexport; source .env; set +o allexport

python3 main.py

last_day=$(ls demo | grep -o 'day[0-9]\+' | sort -V | tail -n 1 | sed 's/day//'); new_day=$((last_day + 1)); cp Exquisite_handout.md demo/day$new_day.md

git add .
git commit -m "update $(ls demo | grep -o 'day[0-9]\+' | sort -V | tail -n 1).md"
git push

python3 notify.py