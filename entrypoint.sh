#!/bin/bash -x

chromedriver &
java -jar selenium-server-standalone-3.141.59.jar &
# Give time for background softwares to start.
sleep 3
cd ./change-analyzer

GENERATE=0
REPLAY=0
COMPARE=0
CSV=0

for i in "$@"; do
  case $i in
    -i=*|--ini=*)
      INI="${i#*=}"
      shift
      echo -e "$INI" > /home/localtester/change-analyzer/input.ini
      ;;
    --csv=*)
      CSV=1
      CSV_PATH="${i#*=}"
      shift
      ;;
    -g*|--generate*)
      GENERATE=1
      shift
      ;;
    -r*|--replay*)
      REPLAY=1
      shift
      ;;
    -c*|--compare*)
      COMPARE=1
      shift
      ;;
    *)
      # Unknown option
      ;;
  esac
done

cat input.ini
. .venv/bin/activate

# Generate
if [ "$GENERATE" = "1" ]; then
    echo "GENERATE"
    ca-run --config input.ini
    FIRST_RECORD=$(ls -l recordings|tail -n1|tr -s " "|cut --delimiter=' ' -f9)
    echo "$FIRST_RECORD" > /home/localtester/next_result.txt
fi

# Replay
if [ "$REPLAY" = "1" ] && [ "$CSV" = "1" ]; then
    echo "REPLAY IMPORTED CSV"
    mkdir -p /home/localtester/change-analyzer/recordings
    cp -r "$CSV_PATH"/recordings /home/localtester/change-analyzer/
    FIRST_RECORD=$(ls -l recordings|tail -n1|tr -s " "|cut --delimiter=' ' -f9)
    ca-run --config input.ini --csv_folder=recordings/"$FIRST_RECORD"
    SECOND_RECORD=$(ls -l recordings|tail -n1|tr -s " "|cut --delimiter=' ' -f9)
    echo "$SECOND_RECORD" > /home/localtester/next_result.txt
elif [ "$REPLAY" = "1" ]; then
    echo "REPLAY"
    FIRST_RECORD=$(ls -l recordings|tail -n1|tr -s " "|cut --delimiter=' ' -f9)
    ca-run --config input.ini --csv_folder=recordings/"$FIRST_RECORD"
    SECOND_RECORD=$(ls -l recordings|tail -n1|tr -s " "|cut --delimiter=' ' -f9)
    echo "$SECOND_RECORD" > /home/localtester/next_result.txt
fi

# Compare
if [ "$COMPARE" = "1" ]; then
    echo "COMPARE"
    ca-compare --sequence1_folder "$FIRST_RECORD" --sequence2_folder "$SECOND_RECORD"
fi
