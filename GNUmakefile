main_pages = 1-4
stem = kSEAL_AdditionalSrc
target = $(stem).txt
.PHONY: all

all: $(stem)_hires.pdf $(stem)_lores.pdf

$(stem)_lores.pdf: $(stem)_tmp_lores.pdf $(stem).txt
	rm -f $@
	pdfattach -replace $(stem)_tmp_lores.pdf $(stem).txt $@

$(stem)_hires.pdf: $(stem)_tmp_hires.pdf $(stem).txt
	rm -f $@
	pdfattach -replace $(stem)_tmp_hires.pdf $(stem).txt $@

$(target): SealSources.txt duplicates.tsv
	python3 ./insert-kseal-dup.py \
		--dup-property-name=kSEAL_AdditionalSrc \
		--seal-sources SealSources.txt \
		--dup-tsv duplicates.tsv \
		--order-values TH-,C-,K-,D- \
		--boiler-plate boiler-plate.txt \
		--eof-line \
		> $@

clean:
	rm -f $(target) *_tmp_*res.pdf *_tmp.pdf

veryclean:
	rm -f SealSources.txt $(target)

SealSources.txt:
	wget -i SealSources.url

$(stem)_tmp_lores.pdf: $(stem).pdf
	rm -f $@
	qpdf \
		--empty --pages \
		$(stem).pdf $(main_pages) \
		kSEAL_AdditionalSrc_Appendix_lores.pdf 1-z \
		-- kSEAL_AdditionalSrc_tmp_lores.pdf

$(stem)_tmp_hires.pdf: $(stem).pdf
	rm -f $@
	qpdf \
		--empty --pages \
		$(stem).pdf $(main_pages) \
		kSEAL_AdditionalSrc_Appendix_hires.pdf 1-z \
		-- kSEAL_AdditionalSrc_tmp_hires.pdf
