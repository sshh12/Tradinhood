import glob
import re
import os


DOC_REGEX = r'(def|class) (\w+\(?.+\)?):\s*"""([\s\S]+?)"""'


def main():

    markdown = []

    for fn in glob.iglob('tradinhood/*.py'):

        if 'init' in fn:
            continue

        markdown.append('# ' + os.path.basename(fn))

        prev_class = None

        with open(fn, 'r') as f:
            code = f.read()

        for match in re.finditer(DOC_REGEX, code):
            doc_type = match.group(1)
            title = match.group(2)
            docs = match.group(3).strip().split('\n')

            indent = 0
            for line in docs:
                if ':' in line:
                    indent = line.rindex(' ')
                    break

            lines = [docs[0]] + [line[indent+1:] for line in docs[1:]]

            if doc_type == 'class' or 'self' not in title:
                markdown.append('### ' + title)
                prev_class = title
            elif prev_class is not None:
                if '__init__' in title or 'from_' in title:
                    title = prev_class + '.' + title
                else:
                    title = prev_class + '(...).' + title

            if title.endswith('(self)'):
                title = title.replace('(self)', '')

            markdown.append('`' + title + '`')
            markdown.append('```\n' + '\n'.join(lines) + '\n```')

    with open('docs/DOCS.md', 'w') as f:
        f.write('\n'.join(markdown))

if __name__ == '__main__':
    main()
