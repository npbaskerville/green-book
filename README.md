# Greenbook - Village show management app

## Installation
```angular2html
conda-lock install -f environment.yml
pip install -e .
```

## Usage
All usages start like this
```angular2html
green-book --show_name SHOWNAME [--location OPTIONAL_LOCALDIR]
```
We omit this below.
### Registration
Run this every time you want to add a new contestant.
```angular2html
register --name "John Smith" --entries=1,14,34A,50,50
```

### Class allocation
Run this once after entries have closed an before the show to generate the allocation of contestants to classes.
This will produce a PDF file with one page per contestant.
```angular2html
allocate [--confirm_reallocation]
```

### Judging
Run this on the day of the show to record the results of the judging.
```angular2html
judge --class 42 --first=31, --second=14,27 --commendations=50
```


### Full worked example
```angular2html
# register
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Aunt Dahlia" --entries=35,4,5,39,40,41,42,43,44,45,53,65,65
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Bettie Beetroot" --entries=1,2,2,5,17,35,47,56,56,65
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Major Marrow" --entries=21,22,30,33,39,40,41,42,43,44,45,46,47,68
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Sean Shortbread" --entries=25A,21,22,30,44,59
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Tommy Tomato" --entries=4,22,33,33,44,46,47,53,56,56,59,52
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Willy Wilja" --entries=25A,26,26,21,44,46,47,53,59,65
greenbook  --location /Users/nick/green-book-testing-29aug register --name "Baby Carrot" --entries=70,72

# run this any time to get entry slips
greenbook  --location /Users/nick/green-book-testing-29aug allocate


# judging
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 1 --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 2 --first=2 --second=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 4 --first=1 --commendations=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 5
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 17 --first=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 21 --first=3 --second=1 --third=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 22 --first=2 --second=1 --third=3

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 25A --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 26 --first=1 --commendations=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 30
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 33 --first=3 --second=1 --third=2

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 35  --commendations=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 39 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 40 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 41 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 42 --second=2 --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 43 --first=2 --commendations=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 44 --first=1 --second=3 --third=2 --commendations=4,5
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 45

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 46 --second=1 --first=2
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 47 --first=3
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 52 --first=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 53 --first=2 --second=1 --third=3
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 56 --commendations=3

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 59 --first=1 --third=2 --second=3
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 65 --first=1 --commendations=2 --second=3 --third=4
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 68 --first=1

greenbook  --location /Users/nick/green-book-testing-29aug judge --class 70 --first=1
greenbook  --location /Users/nick/green-book-testing-29aug judge --class 72 --first=1


# final
greenbook  --location /Users/nick/green-book-testing-29aug final_report
```
