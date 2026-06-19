# Build the formatted GSU dissertation from the source paper qmds.
.PHONY: all chapters figure render clean

all: render

chapters:                 ## regenerate chapters/*.qmd + bibs from Paper1/2/3
	python3 build_chapters.py

figure:                   ## (re)generate the Chapter 3 pooled SDID figure
	python3 gen_ch3_threecity.py

render: chapters figure   ## assemble + render dissertation.pdf
	quarto render dissertation.qmd --to pdf

clean:
	rm -rf chapters/*.qmd pl.bib delhi.bib ktc.bib ch3_threecity.png \
	       dissertation.tex .quarto _freeze *.aux *.bbl *.blg *.log
