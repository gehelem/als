import astroalign as al
import numpy as np
import matplotlib.pyplot as plt
from astropy.io import fits
from tqdm import tqdm

nb_im = np.arange(19) + 2
nb_im_str = []
for i in nb_im:
    nb_im_str.append("%05d" % i)

image = fits.open("light_00001.fit")
rgb_ref = image[0].data
image.close()

plt.ion()
fig = plt.figure()
ax = fig.add_subplot(111)
new_rvb = np.rollaxis((np.array(rgb_ref) / 65535.) ** (1 / 3.), 0, 3)
test = ax.imshow(new_rvb)
plt.draw()
plt.pause(1)

for i in tqdm(nb_im_str):
    image = fits.open("light_" + str(i) + ".fit")
    rgb_new = image[0].data
    image.close()

    p, (pos_img, pos_img_rot) = al.find_transform(rgb_new[1], rgb_ref[1])
    rgb_align = []
    for j in tqdm(range(3)):
        rgb_align.append(al.apply_transform(p, rgb_new[j], rgb_ref[j]) + rgb_ref[j])
        rgb_align[j] = np.where(rgb_align[j] < 65535, rgb_align[j], 65535)
    rgb_ref = rgb_align
    new_rvb = np.rollaxis((np.array(rgb_ref) / 65535.) ** (1 / 3.), 0, 3)
    test = ax.imshow(new_rvb)
    plt.draw()
    plt.pause(0.1)

plt.show()
