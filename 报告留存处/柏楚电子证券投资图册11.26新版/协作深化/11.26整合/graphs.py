"""11.26 native SVG diagrams, generated from shared semantic nodes."""
from pathlib import Path
import json,html,re
from decimal import Decimal
HERE=Path(__file__).resolve().parent
STAGE=HERE.parents[1]
OUT=STAGE/'第三轮'/'charts'
OUT.mkdir(exist_ok=True)
esc=html.escape
specs={
'process':{'title':'从一张板材图到合格工件','period':'2025年报功能披露','evidence':'M1-01、02、11；E01、E02','nodes':[
('图纸与排样',['CAD读图、编辑几何','套料安排板面和材料使用']),('刀路与工艺',['CAM安排穿孔、共边、顺序','管材还需处理焊缝与偏差']),('轨迹与速度',['NC协调机床与驱动运动','激光器供光、切割头聚焦']),('反馈与工件',['电容等传感反馈调节间距','尺寸、边缘和节拍由整机验证'])],
'foot':['标准软件简单安装；整机配置、试切、培训与维护分项承担。','来源：2025年报p5–6、14、18、161–162。工艺结果还受材料、光源和机械条件影响。']},
'contract':{'title':'采购、交付、收入与到账的时点','period':'2025年报销售与会计政策','evidence':'M1-02、03、15；E02–E04、E15','nodes':[
('下单：合同买方',['整机厂采购控制、软件和硬件','加工厂用整机交付工件']),('安装和验收：分合同层',['柏楚供货、组测与现场支持','整机厂配置试切；责任查合同']),('确认收入：按履约',['标准品签收并达到合同标准','其他软件交付；有效期软件激活']),('到账：按结算回款',['年度折扣预估冲收入、实结调整','货款到账独立；售后和质保查条款'])],
'foot':['直销说明柏楚的合同关系，OEM与终端直购收入未完整拆分。','来源：2025年报p14、28、119、161–162、213。箭头表示业务联系，不预设统一账期。']},
'moat':{'title':'工艺适配怎样变成订单、利润和现金','period':'机制检验与2024→2025集团历史','evidence':'M1-01–18；B01、B02、B04、B09、B10','nodes':[
('能力积累 → 加工价值',['控制、传感、工艺库、接口复用','验证工时、合格率、节拍、停机']),('客户选择 → 订单',['比较可交付效果、扣返价与责任','宏石会重选；嘉泰含升级和返利']),('收入 → 毛利',['控制留单、实际配套、规格组合','履约量×净价−增量产品成本']),('毛利 → 经营利润',['承担研发、销售、质保和售后','已进成本的支出不重复扣减']),('利润 → 经营现金',['备货与发货占用存货、应收、票据','到账−采购、人员、税费等付现']),('现金 → 再投入余量',['CFO−购建付现＝简化现金余量','回款需继续支持研发、服务和维护'])],
'foot':['虚线：待项目验证的机制；实线：披露的计量联系；点线：集团历史结果。','2024→2025：主营毛利+3.05亿；CFO+1.52亿；简化现金余量+2.30亿。','案例不能单独归属集团利润。FCFF另从核心NOPAT、折旧、经营资本和资本开支推导。']}}
def wraptext(line,limit):
 parts=re.findall(r"[0-9]+(?:\.[0-9]+)?%?|.",line);out=[];cur="";width=0
 for token in parts:
  tw=sum(.55 if ord(c)<128 else 1 for c in token)
  if cur and width+tw>limit:out.append(cur);cur="";width=0
  cur+=token;width+=tw
 if cur:out.append(cur)
 return out
def diagram(key,s,mobile=False):
 n=len(s['nodes']);w=280 if mobile else 1240
 cols=1 if mobile else (3 if n==6 else 4);rows=(n+cols-1)//cols
 bw=w-40 if mobile else (w-40-(cols-1)*30)/cols
 bh=180 if mobile else 185;gap=48 if mobile else 70
 h=145+rows*(bh+gap)+len(s['foot'])*(44 if mobile else 28)+25
 out=[f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {w} {h}" role="img" aria-labelledby="title desc">',f'<title id="title">{esc(s["title"])}</title><desc id="desc">{esc("；".join(s["foot"]))}</desc>',f'<rect width="{w}" height="{h}" rx="25" fill="#f0f8f5"/>','<defs><marker id="arrow" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8" fill="none" stroke="#377d69" stroke-width="1.4"/></marker></defs>']
 out.append('<g font-family="Microsoft YaHei, sans-serif" fill="#203f37">')
 title=s['title']; chunks=[title[i:i+10] for i in range(0,len(title),10)] if mobile else [title]
 if mobile and key=='moat':chunks=['工艺适配怎样变成','订单、利润和现金']
 for i,line in enumerate(chunks):out.append(f'<text x="20" y="{35+i*31}" font-size="{24 if mobile else 30}" font-weight="700">{esc(line)}</text>')
 for i,(head,lines) in enumerate(s['nodes']):
  col=i%cols;row=i//cols;x=20+col*(bw+30);y=125+row*(bh+gap)
  fill=['#dcefe7','#e3edf9','#eae3f3','#f5ead9'][i%4]
  out.append(f'<rect x="{x}" y="{y}" width="{bw}" height="{bh}" rx="19" fill="{fill}" stroke="#c4dcd1"/>')
  out.append(f'<text x="{x+15}" y="{y+30}" font-size="18" font-weight="700">{esc(head)}</text>')
  for j,line in enumerate(lines):
   # Desktop narrow cards wrap at 16 characters; mobile has more space.
   size=18 if mobile else 20
   limit=11 if mobile else (12 if cols==4 else 17)
   parts=wraptext(line,limit)
   for z,t in enumerate(parts):out.append(f'<text x="{x+15}" y="{y+60+j*(43 if len(lines)>2 else 60)+z*25}" font-size="{size}">{esc(t)}</text>')
  if i<n-1:
   if mobile:line=f'M {w/2} {y+bh+6} v {gap-13}'
   elif col<cols-1:line=f'M {x+bw+5} {y+bh/2} h 21'
   else:line=f'M {x+bw/2} {y+bh+5} v 24 H {20+bw/2} v 35'
   dash=' stroke-dasharray="7 6"' if key=='moat' and i<2 else ''
   out.append(f'<path d="{line}" fill="none" stroke="#377d69" stroke-width="2.5" marker-end="url(#arrow)"{dash}/>')
 fy=125+rows*(bh+gap)+5
 for line in s['foot']:
  pieces=[line[j:j+14] for j in range(0,len(line),14)] if mobile else [line[j:j+63] for j in range(0,len(line),63)]
  for piece in pieces:out.append(f'<text x="20" y="{fy}" font-size="{16 if mobile else 18}" fill="#4d675f">{esc(piece)}</text>');fy+=24
 if key=='moat':
  # The dotted frame marks group historical results, separate from the causal nodes.
  top=125+rows*(bh+gap)-18
  out.append(f'<rect x="12" y="{top}" width="{w-24}" height="{fy-top+6}" rx="12" fill="none" stroke="#699a87" stroke-dasharray="2 5" stroke-width="1.6"/>')
 out.append('</g></svg>')
 # Fit actual wrapped foot height.
 out[0]=out[0].replace(f'{h}" role',f'{max(h,fy+20)}" role');out[2]=out[2].replace(f'height="{h}"',f'height="{max(h,fy+20)}"')
 return ''.join(out)
meta={}
for k,s in specs.items():
 for mobile in [False,True]:(OUT/(k+('-mobile' if mobile else '')+'.svg')).write_text(diagram(k,s,mobile),encoding='utf8')
 meta[k]=dict(title=s['title'],period=s['period'],unit='流程及机制示意',evidence=s['evidence'],blocks=[],file='charts/'+k+'.svg',mobile='charts/'+k+'-mobile.svg')
# Exact cash bridge uses independently extracted audited source cells.
r=json.loads((HERE/'成员2核对/现金桥独立复算.json').read_text(encoding='utf8'))
v=r['results'];meta['cashsurplus']=dict(title='简化现金余量增加来自哪里',period='2024→2025',unit='人民币亿元',evidence='E13、E14；B01、B09；独立现金桥原格',blocks=['B01','B09'],file='charts/cashsurplus.svg',mobile='charts/cashsurplus-mobile.svg')
cells={(x['year'],x['label']):Decimal(x['value'])/Decimal(100000000) for x in r['source_cells']}
cfo={y:cells[y,'经营活动产生的现金流量净额'] for y in [2024,2025]}
cap={y:cells[y,'购建固定资产、无形资产和其他长期资产支付的现金'] for y in [2024,2025]}
sur={y:Decimal(v['现金余量'+str(y)])/Decimal(100000000) for y in [2024,2025]}
dc=Decimal(v['CFO增量'])/Decimal(100000000);dp=Decimal(v['购建减少'])/Decimal(100000000)
cash={'title':meta['cashsurplus']['title'],'nodes':[
 ('2024 简化现金余量',[f'CFO {cfo[2024]:.4f}',f'−购建 {cap[2024]:.4f}',f'＝{sur[2024]:.4f} 亿元']),
 ('经营现金流增加',[f'{cfo[2025]:.4f} − {cfo[2024]:.4f}',f'贡献 +{dc:.4f} 亿元']),
 ('购建付现减少',[f'{cap[2024]:.4f} − {cap[2025]:.4f}',f'贡献 +{dp:.4f} 亿元']),
 ('2025 简化现金余量',[f'{sur[2024]:.4f}＋{dc:.4f}',f'＋{dp:.4f}＝{sur[2025]:.4f} 亿元'])],
 'foot':['原值：2024年报p116–117、2025年报p130，集团合并人民币元；公式差0.00元。','2025应收与存货仍占用资金；购建下降含单年节奏。维护与扩张投入未拆分，本图不等于FCFF。']}
for mobile in [False,True]:(OUT/('cashsurplus'+('-mobile' if mobile else '')+'.svg')).write_text(diagram('cashsurplus',cash,mobile),encoding='utf8')
meta['memberoriginal']=dict(title='成员一原图：工艺适配怎样影响整机厂续购',period='2026-11-26成员一原成果',unit='机制示意',evidence='M1-01–04、09、10',blocks=[],file='../协作深化/成员一/护城河因果图.svg')
(HERE/'新增图表映射.json').write_text(json.dumps(meta,ensure_ascii=False,indent=2),encoding='utf8')
