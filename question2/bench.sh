set -e
URL=http://localhost:8000/predict
N=${N:-20}

time_one() {   # $1 = text
  curl -s -o /dev/null -X POST $URL -H 'Content-Type: application/json' \
       -d "{\"text\":\"$1\"}" -w '%{time_total}\n'
}

time_one "warm up the interpreter" > /dev/null
docker compose exec -T cache redis-cli FLUSHALL > /dev/null

for i in $(seq $N); do time_one "WIN a FREE prize number $i at bit.ly/xyz$i"; done \
  | awk -v n=$N '{s+=$1} END {printf "MISS avg %.2f ms over %d requests\n", s/n*1000, n}'

for i in $(seq $N); do time_one "WIN a FREE prize number $i at bit.ly/xyz$i"; done \
  | awk -v n=$N '{s+=$1} END {printf "HIT  avg %.2f ms over %d requests\n", s/n*1000, n}'

echo "--- single request, shows the cached flag ---"
curl -s -X POST $URL -H 'Content-Type: application/json' \
     -d '{"text":"WIN a FREE prize number 1 at bit.ly/xyz1"}'; echo