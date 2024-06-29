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
