kseal_additional.tsv: SealSources.txt duplicates.tsv
	python3 ./insert-kseal-dup.py \
		--dup-property-name=kSEAL_AdditionalSrc \
		--seal-sources SealSources.txt \
		--dup-tsv duplicates.tsv \
		--boiler-plate boiler-plate.txt \
		> $@

clean:
	rm -f kseal_additional.tsv

veryclean:
	rm -f SealSources.txt kseal_additional.tsv

SealSources.txt:
	wget -i SealSources.url

