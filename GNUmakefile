target = kSEAL_AdditionalSrc.txt

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
	rm -f $(target)

veryclean:
	rm -f SealSources.txt $(target)

SealSources.txt:
	wget -i SealSources.url

