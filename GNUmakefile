kseal_additional.tsv: SealSources.txt duplicates.tsv
	python3 ./insert-kseal-dup.py \
		--dup-property-name=kSEAL_AdditionalSrc \
		--seal-sources SealSources.txt \
		--dup-tsv duplicates.tsv \
		> $@

SealSources.txt:
	wget -i SealSources.url

