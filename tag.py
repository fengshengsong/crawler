import sys
import os
sys.path.append('../')

import jieba 
import jieba.analyse

file_name = 'essays.txt'
file_path = os.path.join(os.path.dirname(__file__),file_name)
content = open(file_name,'r').read() 

tags = jieba.analyse.extract_tags(content,topK=20,withWeight=True, allowPOS=())
tagss = jieba.analyse.textrank(content, topK=5, withWeight=True, allowPOS=('ns', 'n', 'vn', 'v'))

print(tags)