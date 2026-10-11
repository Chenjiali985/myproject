# 一次性拆分脚本：seed_data.py -> seed_content.py + 精简 seed_data.py
lines = open('seed_data.py', encoding='utf-8').read().split('\n')
start = next(i for i, l in enumerate(lines) if l.startswith('SEED_POSTS = ['))
end = next(i for i, l in enumerate(lines) if l.startswith('def seed_if_empty'))

data_block = '\n'.join(lines[start:end]).rstrip() + '\n'
header = '\n'.join(lines[:start]).rstrip() + '\n'
logic = '\n'.join(lines[end:])

with open('seed_content.py', 'w', encoding='utf-8') as f:
    f.write('"""种子数据：与初始化逻辑分离，内容修改不影响代码。"""\n\n\n' + data_block)

with open('seed_data.py', 'w', encoding='utf-8') as f:
    f.write(header + '\nfrom seed_content import SEED_COMMENTS, SEED_POSTS\n\n\n' + logic)

print('split ok, seed_data:', len(header + logic), 'chars')
