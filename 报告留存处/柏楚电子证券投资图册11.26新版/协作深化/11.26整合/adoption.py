"""Record actual chapter adoption and source locators; preserve originals."""
from pathlib import Path
import json,re,csv,html
H=Path(__file__).resolve().parent;STAGE=H.parents[1];D3=STAGE/'第三轮'
a=json.loads((H/'成员1核对/成员一逐项核对.json').read_text(encoding='utf8'))
paragraphs=[]
for p in sorted((D3/'chapters').glob('*.md')):
 for n,s in enumerate(p.read_text(encoding='utf8').split('\n\n'),1):paragraphs.append((p.stem,n,s))
impact={1:'让加工功能与验收条件具体可辨',2:'区分合同买方、使用者与整机责任',3:'将净收入、折扣、验收与到账分开',4:'将复用机制接到费用资本后的回报',5:'用产品代际和压力期检验延续',6:'以功能集成反例约束配套推断',7:'出货组比保留结构身份',8:'新业务按研发、方案、验收分阶段',9:'买方重选限制锁定与定价权判断',10:'同控制可选头约束软硬协同',11:'明确光源、切割头、机床和控制分工',12:'功率段候选与实际替代分开',13:'分开弧焊与激光焊接工位',14:'展示不直接等于跨客户商业化',15:'分开场景、单品、市场及客户分母',16:'预测摘录仅条件复算，不改模型',17:'同机型选项不等于成交结果',18:'持续采购与规格、返利和多供方并读'}
rows=[]
for c in a['claims']:
 ident=c['id'];hits=[x for x in paragraphs if ident in x[2]]
 assert hits,ident
 first=hits[0];num=int(ident[-2:]);current='；'.join('第'+x[0]+'章段'+str(x[1]) for x in hits)
 rows.append(dict(编号=ident,原主张=c['original_interpretation'],原页或原表=c['source_locator'],处理='实质采用；原文缺项按证据身份收窄' if num in [12,13,14,16,17] else '实质采用并衔接经济回报',实际改写=first[2],改前位置='11.25第三轮/chapters/'+first[0]+'.md（一般性经营或竞争优势段）',改后位置=current,报告段落='第三轮/chapters/'+first[0]+'.md，段'+str(first[1]),图册锚点='#ch'+first[0],证据锚点='#'+ident,判断影响=impact[num],支持范围=c['support_limit']))
with (H/'逐条采用表.csv').open('w',encoding='utf-8-sig',newline='') as f:
 w=csv.DictWriter(f,rows[0].keys(),lineterminator='\n');w.writeheader();w.writerows(rows)
(H/'逐条采用表.json').write_text(json.dumps(rows,ensure_ascii=False,indent=2),encoding='utf8')
def table(headers,data):return '| '+' | '.join(headers)+' |\n| '+' | '.join('---' for _ in headers)+' |\n'+'\n'.join('| '+' | '.join(str(x).replace('|','／').replace('\n',' ') for x in row)+' |' for row in data)
md='# 成员一M1-01至M1-18实际采用表\n\n2026-11-26，成员四Codex实施Agent按实际成品登记。原成员一十文件以63fc83d原字节保留；当前文件没有覆盖原会话与审核历史。\n\n'
md+=table(['编号','原主张与原页','实际改写及位置','判断影响'],[[r['编号'],r['原主张']+' '+r['原页或原表'],r['实际改写']+' '+r['改后位置'],r['判断影响']] for r in rows])
md=md.replace('](复核.py)','](../成员一/复核.py)')
md=re.sub(r'\]\(#([^)]*)\)',r'](../成员一/证据与改判.md#\1)',md)
md+='\n\n完整字段含改前、改后、章节段号、图册与证据锚点，见[CSV](逐条采用表.csv)。段号按章节空行分段，表格和图位亦单独计段。\n'
(H/'逐条采用表.md').write_text(md,encoding='utf8')
arts=[]
locations=['ch01与ch02；M1-01、11、15','ch07配置竞争段；M1-09、12、17','ch07工艺与新业务段；M1-04、14','ch02集中度及ch07重选；M1-15、18','ch07焊接工位；M1-08、13','ch07改判表、ch09预测入口；M1-16','ch07新业务及预测附件；M1-16','ch07历史起点及预测附件；M1-05、16']
for i,x in enumerate(a['articles']):
 parts=[v.strip() for v in x['original_row'].strip('|').split('|')]
 arts.append(dict(文章=x['id'],出处=parts[0],原设问=parts[1],成员一整理观点=parts[2],原文=parts[3],本版采用位置=locations[i],实际处置='设问与框架采用；公司数值回年报。'+('历史预测仅条件对照，公众号原文未取得。' if i>=6 else '原估值、份额不进入模型。'),缺项='行业原表及同口径分母、适用工位、采用率、每站套数与实结价；同机型验收/回款。'+('另缺全文日期和预测原表。' if i>=6 else '')))
(H/'八篇文章采用表.json').write_text(json.dumps(arts,ensure_ascii=False,indent=2),encoding='utf8')
(H/'八篇文章采用表.md').write_text('# 八篇文章的设问、观点与实际采用\n\n保留成员一逐篇阅读与当时采纳记录。六篇雪球仅吸收设问和框架，两公众号预测原文当前受验证阻挡，摘录留作条件算术。\n\n'+table(list(arts[0]),[list(x.values()) for x in arts]),encoding='utf8')
# All formal locators resolve to bundled originals; original member handoff is archival.
annual=list((STAGE/'第四轮/年报原件').glob('*.pdf'))
def af(y):
 q=[p for p in annual if str(y) in p.name];assert q,(y,[p.name for p in annual]);return q[0].name
external={p.name:p for p in (H/'成员1核对/公开补证原件').glob('*.pdf')}
def ext(part,page):
 p=next(p for n,p in external.items() if part in n)
 return '协作深化/11.26整合/成员1核对/公开补证原件/'+p.name+'#page='+str(page)
locs={
1:[(2025,14),(2025,18)],2:[(2025,14),(2025,161)],3:[(2025,161),(2025,162),(2025,213)],4:[(2019,30),(2025,16),(2025,40)],5:[(2019,11),(2021,12),(2022,26),(2023,14)],6:[(2024,26),(2025,16),(2025,29)],7:[(2024,26),(2025,29)],8:[(2020,34),(2025,13),(2025,16)],11:[(2025,14),(2025,18)],13:[(2025,13),(2025,16)],14:[(2025,16),(2025,40)],15:[(2025,27),(2025,28),(2025,30)],16:[(2025,8),(2025,28)]}
body='<section class="chapter" id="m1-evidence"><h1>成员一证据与采用位置</h1><p>披露、买方说明、复算、机制推断与模型假设分别识别。十八项完整采用表和八篇文章追踪可下载；必要限定在正文可见。原十份交接保留11.25基线名称，属于历史原稿。</p><p><a href="协作深化/11.26整合/逐条采用表.md">逐条采用表</a> · <a href="协作深化/11.26整合/八篇文章采用表.md">八篇文章采用</a> · <a href="协作深化/成员一/README.md">十份原交接</a> · <a href="协作深化/11.26整合/成员3核对/预测连接复核.md">预测原文缺口与变量连接</a></p><div class="table-scroll"><table><thead><tr><th>编号与采用</th><th>原页入口</th><th>支持边界与判断影响</th></tr></thead><tbody>'
for r in rows:
 n=int(r['编号'][-2:]);links=[f'<a href="第四轮/年报原件/{af(y)}#page={p}">{y}年报p{p}</a>' for y,p in locs.get(n,[])]
 if n==9:links+=[f'<a href="{ext("宏石激光_招股书",160)}">宏石注册稿p160</a>',f'<a href="{ext("宏石激光_招股书",165)}">同类分母p165</a>',f'<a href="{ext("深交所",96)}">窄口径p96</a>']
 if n==10:links+=[f'<a href="{ext("FSCUT8000",5)}">8000A手册p5</a>']
 if n==18:links+=[f'<a href="{ext("嘉泰激光_招股",100)}">嘉泰采购p100</a>',f'<a href="{ext("嘉泰激光_审核",57)}">适配p57</a>',f'<a href="{ext("嘉泰激光_审核",60)}">多供方与均价p60</a>',f'<a href="{ext("嘉泰激光_审核",68)}">规格返利p68</a>',f'<a href="{ext("嘉泰激光_招股",111)}">合同p111</a>']
 if n in [12,13,14,16,17]:links.append('<a href="协作深化/成员一/证据与改判.md">原出处及缺项</a>')
 body+=f'<tr id="{r["编号"]}"><td><strong>{r["编号"]}</strong><br><a href="{r["图册锚点"]}">{r["改后位置"]}</a></td><td>'+ ' · '.join(links)+'</td><td>'+html.escape(r['支持范围']+'；'+r['判断影响'])+'</td></tr>'
body+='</tbody></table></div><p><a href="协作深化/11.26整合/成员1核对/采购原格独立核验.json">采购原格复算</a> · <a href="协作深化/11.26整合/成员2核对/现金桥独立复算.json">现金桥原值、公式与零差</a> · <a href="协作深化/11.26整合/成员2核对/动态Fact核验.json">当前Fact绑定</a> · <a href="协作深化/11.26整合/验收记录.md">11.26实际验收</a></p></section>'
(H/'证据索引.html').write_text(body,encoding='utf8')
print('18 claims and 8 articles mapped to actual chapters')
