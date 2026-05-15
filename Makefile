LIB=span_panel.py
TARGETS=get_circuit_info

all:	$(TARGETS)

get_circuit_info:	get_circuit_info.py $(LIB)
	rm -fr $@.build && mkdir $@.build && cp $^ $@.build && (cd $@.build && mv $< __main__.py && echo '#!/usr/bin/python3'; zip - *) | cat > $@ && chmod +x $@

clean:
	rm -fr *~ *.build get_circuit_info

.PHONY:	all clean
