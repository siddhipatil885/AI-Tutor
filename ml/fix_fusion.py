import re
content = open(r'src/train_fusion.py', encoding='utf-8').read()
content = re.sub(r',\s*multi_class="multinomial"', '', content)
open(r'src/train_fusion.py', 'w', encoding='utf-8').write(content)
print('fixed')
