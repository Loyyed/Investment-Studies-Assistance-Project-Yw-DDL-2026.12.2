"""Publish the five browsable case editions and the file-level acceptance matrix."""
from pathlib import Path
import json
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(ROOT/'app'),str(ROOT/'shared/runtime'),str(ROOT/'scripts')]
from case_model import OUT,CODES,get_records,group
from case_site import overview,render_case,matrix_svg,markdown_sections,NAV
from atlas_render import mast,page
from atlas_render import csv_payload
from atlas_service import json_bytes

OPERATING = {
 '002507':('operating-analysis.json','rebuild_operations.py','新增直销毛利21.09百万元；基地资金余额与集团资本开支分栏'),
 '600298':('operating-analysis.json','rebuild_operations.py','吨成本下降抵消吨均价压力；产线转固与尚在建分批'),
 '688188':('operating-summary.json','operating.py','主营毛利率下降由产品组合和分部内毛利共同造成'),
 '09992':('operating-summary.json','operating.py','IP接续、海外线上回落和经营租赁分拆；组合Q4条件可回代'),
 'US':('independent-valuation.json','audit_isrg.py','租赁变动收入503.8与非现金设备转入670.5应用各自出口'),
}


def get(path):
    return json.loads(path.read_text(encoding='utf-8'))


def rows():
    annual=get_records(15,'annual')
    recent=get_records(15,'interim')
    for code in CODES:
        base=OUT/code
        model=get(base/'model.json')
        comp=model['company']
        old=model['cases']['base']
        periods=group(annual,comp)
        inter=group(recent,comp)
        terms=model['tests']['boundary']
        count=sum(len(x['roots']) for x in terms)
        evidence, program, finding=OPERATING[code]
        checks=[
         ('长历史','history.csv',f'{len(periods)}个财年；损益、CFO与运营资本范围保留','发布底表；FCFF缺项留空'),
         ('近期披露','interim.csv',f'{len(inter)}个可比期；单期、累计、同比和期末分栏','发布底表；波动归因按口径'),
         ('商业模式与竞争','case.md',finding,'经营解释；反方和下一披露见正文'),
         ('收入拆解',evidence,'业务量、组均价/结构或业务组合按可见口径拆解','表中逐项保留未知归属'),
         ('成本与分析EBIT','history.csv','各财年合并成本、费用、报告营业利润、分析EBIT、未分拆残差','代理；公司专项表保留原科目'),
         ('渠道/单位经济',evidence,finding,'条件测试；未公开单体经济不归给单体'),
         ('现金与资本','history.csv','按报告CFO对读；股数、净债务、租赁与权益桥可追踪','部分年度分项披露不足'),
         ('三条预测复算','forecast.csv',f"最新 {model['source_windows']['latest_disclosed_period']}；2027–2031三情景；基准 {old['per_share']:.8f}",'程序可复算'),
         ('估值反推','reverse.csv',f"回代 {count} 组；{model['security']['quote']} 收盘 {model['close']:.2f}",'条件估值；无解保留端点'),
         ('原文与独立复核','independent-review.md','每家公司至少一条原文至模型的独立复核','原披露／算术／代理分标'),
         ('图册', 'index.html','同日情景、双变量图、原文和底表相联','在线与离线版'),
         ('素材地图','report-map.md','未来章节、证据、要补材料与待分配角色','供团队择一后写正式稿'),
        ]
        assert (base/program).is_file(),program
        for area,rel,actual,status in checks:
            if rel=='index.html':
                assert (base/'case.md').is_file()
            else:
                assert (base/rel).is_file(),(code,rel)
            yield dict(code=code,company=comp,area=area,file=f'{code}/{rel}',actual=actual,status=status)


def publish():
    for code in CODES:
        case=OUT/code
        m=get(case/'model.json')
        (case/'sensitivity.svg').write_text(matrix_svg(m['tests'],m['security']['quote']),encoding='utf-8',newline='\n')
        html=render_case(ROOT,OUT,code)
        (case/'index.html').write_text(html,encoding='utf-8',newline='\n')
    (OUT/'index.html').write_text(overview(ROOT,OUT),encoding='utf-8',newline='\n')
    for label,title in (('motion','动效与预览'),('review','组长待审与下一步')):
        toc,body,_=markdown_sections(ROOT,OUT/(label+'.md'),label)
        (OUT/(label+'.html')).write_text(page(ROOT,title,mast(title,'五家公司证券投资案例','2026-11-12',NAV)+
            '<main class="shell note">'+toc+body+'</main>'),encoding='utf-8',newline='\n')
    matrix=list(rows())
    assert len(matrix)==60
    (OUT/'acceptance.csv').write_bytes(csv_payload(matrix))
    files=sorted(f.relative_to(OUT).as_posix() for f in OUT.rglob('*') if f.is_file()
                 and not any(x.startswith('.') or x=='__pycache__' for x in f.relative_to(OUT).parts)
                 and f.suffix in ('.html','.csv','.md','.json','.svg','.py','.png','.jpg'))
    files=list(dict.fromkeys([*files,'case-package.json']))
    (OUT/'case-package.json').write_bytes(json_bytes(dict(cutoff='2026-11-12',companies=list(CODES),files=files)))
    print(f'{len(matrix)}项逐公司验收；{len(files)}个发布资源')


if __name__=='__main__':
    publish()
