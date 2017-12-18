for f in $(find . -type f -name "*.png")
do
echo "Processing $f ..."
convert -strip $f ${f/.png/.bmp}
done

for f in $(find . -type f -name "*.gif")
do
echo "Processing $f ..."
convert -strip $f ${f/.gif/.bmp}
done