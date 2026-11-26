import pymupdf
from pathlib import Path
p=Path(r'D:/投资学/.bochu1126-member1-check')
for f,n in [('宏石激光_招股书注册稿_2023-10-12.pdf',160),('嘉泰激光_招股说明书申报稿_2026-06-22.pdf',100)]:
 d=pymupdf.open(p/'公开补证原件'/f);d[n-1].get_pixmap(matrix=pymupdf.Matrix(1.5,1.5)).save(p/f'{n}.png')
