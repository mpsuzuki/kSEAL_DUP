kseal_dupsrc.tsv: SealSources.txt duplicates.tsv
	python3 ./insert-kseal-dup.py \
		--seal-sources SealSources.txt \
		--dup-tsv duplicates.tsv \
		> kseal_dupsrc.tsv

SealSources.txt:
	wget -i SealSources.url

