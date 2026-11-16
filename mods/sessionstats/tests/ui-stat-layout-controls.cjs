/* Statistic text is centered as one readable block; table rows share the finance height. */
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
async function naturalKPIBoxes(page){
  return page.locator('#ss-groups .ss-group-kpi .ss-kpi-label,#ss-groups .ss-group-kpi .ss-kpi-value').evaluateAll(nodes=>nodes.length===6&&nodes.every(node=>{
    const range=document.createRange();range.selectNodeContents(node);
    const rectangles=[...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0).sort((a,b)=>a.top-b.top),lines=[];
    for(const rect of rectangles)if(!lines.length||rect.top-lines[lines.length-1]>1)lines.push(rect.top);
    const style=getComputedStyle(node),scale=parseFloat(getComputedStyle(document.documentElement).fontSize);
    return lines.length>0&&node.getBoundingClientRect().height<=lines.length*parseFloat(style.lineHeight)+scale;
  }));
}
module.exports=async({browser,nativeHost,check})=>{
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale}});
    let sequence=0;
    try{
      await page.evaluate(scale=>{
        const payload=JSON.parse(model.payload),scope=payload.scopes.launch,item=scope.maps[0],stats=item.stats;
        payload.account_key='synthetic-stat-layout-'+scale;payload.window_size=[1800,1100];
        payload.localization={language:'en',messages:{}};
        item.id='synthetic-stat-layout';item.name='Synthetic map';stats.battles=stats.observed_battles=4;
        stats.wn8=750;stats.wn8_count=4;
        const ranges={xp_base:[100,250,400,1000],xp_received:[200,500,800,2000],battle_wn8:[300,750,1200,3000],
          credits_income_base:[10000,12500,15000,50000],credits_income_received:[15000,22500,30000,90000],
          credits_net_base:[6000,7500,9000,30000],credits_net_received:[11000,17500,24000,70000],
          credits_costs:[4000,5000,6000,20000]};
        item.extrema_battles={};
        for(const [metric,[min,avg,max,sum]]of Object.entries(ranges)){
          stats[metric]={count:4,min,avg,max,sum};item.extrema_battles[metric]={};
          for(const statistic of ['min','max'])item.extrema_battles[metric][statistic]={
            id:'synthetic-layout-'+metric+'-'+statistic,name:'Synthetic tank',map:'Synthetic map',started_at:1700000000,
            metric,statistic,value:stats[metric][statistic]};
        }
        stats.currencies={credits:{income_base:50000,income_base_count:4,net_base:30000,net_base_count:4,
          income:90000,income_count:4,costs:20000,costs_count:4,net:70000,net_count:4},
          bonds:{income:4,income_count:4,costs:0,costs_count:4,net:4,net_count:4},
          gold:{income:0,income_count:4,costs:0,costs_count:4,net:0,net_count:4}};
        scope.maps=[item];scope.pagination.maps={page:0,pages:1,total:1,page_size:40};
        scope.summary=JSON.parse(JSON.stringify(stats));
        window.__statLayoutFixture=JSON.parse(JSON.stringify(payload));
      },scale);
      async function publish(metric,statistic,options={}){
        await page.evaluate(({metric,statistic,options,sequence})=>{
          const payload=JSON.parse(JSON.stringify(__statLayoutFixture)),scope=payload.scopes.launch,item=scope.maps[0];
          scope.ordering.maps={metric,statistic,direction:'desc',chronology:'newest'};scope.data_revision='stat-layout-'+sequence;
          if(options.partial)item.stats.credits_net_received.count=2;
          if(options.pending)item.stats.observed_battles=6;
          if(options.noSources)delete item.extrema_battles;
          if(options.name)item.name=options.name;
          if(options.width){payload.account_key+='-profile-'+sequence;payload.window_size=[options.width,1100];}
          if(options.count!==undefined)item.stats.battles=item.stats.observed_battles=options.count;
          if(options.empty){
            const stats=item.stats;stats.battles=stats.wins=stats.losses=stats.draws=stats.wn8_count=0;
            stats.observed_battles=137;stats.wn8=stats.win_rate=null;
            for(const data of Object.values(stats))if(data&&typeof data==='object'&&typeof data.count==='number'){
              data.count=0;data.min=data.avg=data.max=data.sum=null;
            }
            for(const data of Object.values(stats.currencies))for(const field of ['income','costs','net','income_base','net_base']){
              data[field]=null;data[field+'_count']=0;
            }
          }
          if(options.large){
            item.stats.observed_battles=6;
            const amount=-1234567890,stats=item.stats;
            stats.credits_net_received={count:3,min:amount,avg:amount,max:amount,sum:amount*3};
            stats.currencies.credits.income=61728440;stats.currencies.credits.costs=5000000000;
            stats.currencies.credits.net=amount*3;stats.currencies.credits.net_count=3;stats.currencies.credits.income_base=40000000;
            stats.currencies.credits.net_base=-4960000000;
            for(const statistic of ['min','max'])item.extrema_battles.credits_net_received[statistic].value=amount;
          }
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
        },{metric,statistic,options,sequence:++sequence});
        await page.locator('#ss-group-maps').click();await frames(page);
      }
      for(const [metric,statistic,options]of [['credits_costs','max',{}],['credits_income_received','min',{}],
        ['credits_income_received','avg',{}],['credits_net_received','max',{partial:true}],['xp_received','sum',{}],
        ['xp_received','min',{}],['battle_wn8','avg',{}],['off','avg',{}]]){
        await publish(metric,statistic,options);
        const geometry=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
          const header=card.querySelector('.ss-group-header').getBoundingClientRect(),badge=card.querySelector('.ss-group-sort-value');
          const name=card.querySelector('.ss-group-name').getBoundingClientRect(),stats=card.querySelector('.ss-group-stats').getBoundingClientRect();
          const identity=card.querySelector('.ss-group-name'),walker=document.createTreeWalker(identity,NodeFilter.SHOW_TEXT),used=[];
          let part;while((part=walker.nextNode()))if(part.textContent.trim()){
            const text=document.createRange();text.selectNodeContents(part);used.push(...text.getClientRects());
          }
          for(const icon of identity.querySelectorAll('.ss-vehicle-icon,.ss-info-button'))used.push(icon.getBoundingClientRect());
          const result={header:header.height/scale,card:card.getBoundingClientRect().height/scale,
            identityWidth:name.width/scale,identityUsed:(Math.max(...used.map(rect=>rect.right))-name.left)/scale,
            kpiWidths:[...card.querySelectorAll('.ss-group-kpi')].map(node=>node.getBoundingClientRect().width/scale),
            content:Math.max(name.height,stats.height)/scale,badge:null};
          if(badge){
            const caption=badge.querySelector('.ss-group-sort-caption'),value=badge.querySelector('.ss-group-sort-number'),box=badge.getBoundingClientRect();
            const ink=node=>{const range=document.createRange();range.selectNodeContents(node);return {box:range.getBoundingClientRect(),lines:[...range.getClientRects()]};};
            const title=ink(caption),number=ink(value),top=Math.min(title.box.top,number.box.top),bottom=Math.max(title.box.bottom,number.box.bottom);
            const titleLines=ink(caption.querySelector('.ss-group-sort-caption-text')||caption).lines;
            const icon=caption.querySelector('.ss-sort-partial-icon'),textBox=(caption.querySelector('.ss-group-sort-caption-text')||caption).getBoundingClientRect(),iconBox=icon&&icon.getBoundingClientRect();
            result.badge={height:box.height/scale,captionLines:titleLines.length,
              partial:caption.querySelectorAll('.ss-sort-partial-icon').length===1&&!caption.textContent.includes('*'),
              iconAdjacent:!iconBox||(Math.abs((iconBox.left-textBox.right)/scale-4)<=0.5&&
                Math.abs((iconBox.top+iconBox.bottom-textBox.top-textBox.bottom)/2)<=scale&&iconBox.right<=box.right+scale),
              captionHeight:caption.getBoundingClientRect().height/scale,valueHeight:value.getBoundingClientRect().height/scale,
              centered:Math.abs((top+bottom)/2-(box.top+box.bottom)/2)<=1.5*scale,
              separate:title.box.bottom<=number.box.top+scale,
              fits:title.lines.concat(number.lines).every(rect=>rect.left>=box.left-scale&&rect.right<=box.right+scale&&rect.top>=box.top-scale&&rect.bottom<=box.bottom+scale)};
          }
          return result;
        },scale);
        check('The headline reserves only its actual content height '+metric+'/'+statistic+'/'+scale,
          geometry.header>=geometry.content&&geometry.header<=geometry.content+3);
        check('The familiar KPI columns retain compact widths while the identity takes spare space '+metric+'/'+statistic+'/'+scale,
          geometry.kpiWidths.length===3&&geometry.kpiWidths.every((width,index)=>Math.abs(width-[60,62,72][index])<=0.5));
        check('KPI labels and figures use natural text height instead of blank fixed rows '+metric+'/'+statistic+'/'+scale,await naturalKPIBoxes(page));
        if(geometry.badge){
          const b=geometry.badge;
          check('The statistic frame fits its centered caption and value with small padding '+metric+'/'+statistic+'/'+scale+': '+JSON.stringify(b),
            b.height>=b.captionHeight+b.valueHeight+5&&b.height<=b.captionHeight+b.valueHeight+7&&
            b.centered&&b.separate&&b.fits&&b.iconAdjacent&&b.valueHeight<=20);
          if(metric==='credits_costs')check('A short statistic caption uses one centered line at '+scale,b.captionLines===1);
          if(metric==='credits_income_received')check('A longer statistic caption widens its own column without wrapping at '+scale,b.captionLines===1);
          if(options.partial)check('A partial statistic keeps its marker inside the centered block at '+scale,b.partial);
        }
        if(metric==='credits_costs'&&scale===1){
          const obsolete=await page.addStyleTag({content:'.ss-aggregate .ss-kpi-label { height:26px !important; min-height:26px !important; } .ss-aggregate .ss-kpi-value { height:38px !important; min-height:38px !important; }'});
          check('The natural-height guard rejects the old empty KPI label/value slots',!await naturalKPIBoxes(page));
          await obsolete.evaluate(node=>node.remove());
          check('Removing old fixed slots restores the compact KPI height',await naturalKPIBoxes(page));
        }
      }
      await publish('credits_net_received','max',{large:true});
      const large=await page.locator('#ss-groups .ss-group-sort-value').evaluate((badge,scale)=>{
        const box=badge.getBoundingClientRect(),caption=badge.querySelector('.ss-group-sort-caption'),value=badge.querySelector('.ss-group-sort-number');
        const ink=node=>{const range=document.createRange();range.selectNodeContents(node);return [...range.getClientRects()];};
        const title=ink(caption),number=ink(value),text=title.concat(number),top=Math.min(...text.map(r=>r.top)),bottom=Math.max(...text.map(r=>r.bottom));
        return {captionLines:ink(caption.querySelector('.ss-group-sort-caption-text')||caption).length,valueLines:number.length,
          partial:caption.querySelectorAll('.ss-sort-partial-icon').length===1&&!caption.textContent.includes('*'),height:box.height/scale,
          captionHeight:caption.getBoundingClientRect().height/scale,valueHeight:value.getBoundingClientRect().height/scale,
          value:value.textContent.replace(/\s/g,''),centered:Math.abs((top+bottom)/2-(box.top+box.bottom)/2)<=1.5*scale,
          fits:text.every(rect=>rect.left>=box.left-scale&&rect.right<=box.right+scale&&rect.top>=box.top-scale&&rect.bottom<=box.bottom+scale)};
      },scale);
      check('A signed ten-digit value and partial warning remain fully visible in a content-sized badge at '+scale+': '+JSON.stringify(large),
        large.captionLines>=1&&large.valueLines>=1&&large.partial&&large.value==='-1234567890'&&
        large.height>=large.captionHeight+large.valueHeight+5&&large.height<=large.captionHeight+large.valueHeight+7&&large.centered&&large.fits);
      await publish('credits_costs','max');
      const table=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
        const performance=card.querySelector('.ss-performance'),economy=card.querySelector('.ss-economy'),
          left=performance.getBoundingClientRect(),right=economy.getBoundingClientRect(),rows=[...performance.querySelectorAll('.ss-metric-head,.ss-metric-row')].map(node=>node.getBoundingClientRect());
        const gaps=rows.slice(1).map((row,index)=>(row.top-rows[index].bottom)/scale),top=(rows[0].top-left.top)/scale,bottom=(left.bottom-rows[rows.length-1].bottom)/scale;
        return {fill:Math.abs(left.top-right.top)<=scale&&Math.abs(left.bottom-right.bottom)<=scale&&left.right<=right.left+scale,
          gaps,top,bottom,rows:rows.length,distributed:getComputedStyle(performance).justifyContent==='space-around',
          contained:rows.every(row=>row.top>=left.top-scale&&row.bottom<=left.bottom+scale&&row.left>=left.left-scale&&row.right<=left.right+scale),
          coverage:card.querySelectorAll('.ss-cell-coverage,.ss-count-coverage,.ss-wn8-coverage').length,height:card.getBoundingClientRect().height/scale};
      },scale);
      check('Performance fills the adjacent financial table height without overlapping columns at '+scale+': '+JSON.stringify(table),table.fill&&table.contained&&table.rows===4);
      check('Performance rows distribute their available space evenly at '+scale,
        table.distributed&&table.gaps.every(gap=>gap>=0)&&Math.max(...table.gaps)-Math.min(...table.gaps)<=1.5&&
        Math.abs(table.top-table.bottom)<=1.5&&Math.abs(table.gaps[1]-(table.top+table.bottom))<=1.5);
      const rules=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
        const rows=[...card.querySelectorAll('.ss-metric-row,.ss-money-row')],
          cells=[...card.querySelectorAll('.ss-metric-head > .ss-metric-number,.ss-metric-row > .ss-metric-number,.ss-money-head > .ss-money-value,.ss-money-row .ss-money-value')],
          labels=[...card.querySelectorAll('.ss-metric-name,.ss-money-label')];
        const rowDividers=[...card.querySelectorAll('.ss-credit-column > .ss-money-value + .ss-money-value,.ss-credit-row-label + .ss-credit-row-label')],
          borderOwners=cells;
        const horizontal=rows.concat(rowDividers).map(node=>getComputedStyle(node)),vertical=borderOwners.map(node=>getComputedStyle(node));
        return {rows:rows.length,logicalRows:rows.reduce((count,row)=>count+(row.classList.contains('ss-credit-pair')?2:1),0),cells:cells.length,verticalOwners:vertical.length,
          horizontal:horizontal.every(css=>Math.abs(parseFloat(css.borderTopWidth)/scale-1)<=0.1&&css.borderTopStyle==='solid'),
          vertical:vertical.every(css=>Math.abs(parseFloat(css.borderLeftWidth)/scale-1)<=0.1&&css.borderLeftStyle==='solid'),
          sameColor:horizontal.concat(vertical).every(css=>(css.borderTopWidth!=='0px'?css.borderTopColor:css.borderLeftColor)==='rgb(60, 68, 52)'),
          unframed:labels.every(node=>parseFloat(getComputedStyle(node).borderLeftWidth)===0)&&
            cells.every(node=>parseFloat(getComputedStyle(node).borderRightWidth)===0)};
      },scale);
      check('Performance and finance tables use matching thin cell rules without outer frames at '+scale+': '+JSON.stringify(rules),
        rules.rows===5&&rules.logicalRows===6&&rules.cells===23&&rules.verticalOwners===23&&rules.horizontal&&rules.vertical&&rules.sameColor&&rules.unframed);
      const actions=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
        const performance=[...card.querySelectorAll('.ss-metric-row .ss-extreme-cell')],
          finance=[...card.querySelectorAll('.ss-credit-extreme-actions')];
        return {performance:performance.length,finance:finance.length,
          arrows:performance.every(cell=>{
            const button=cell.querySelector('.ss-metric-battle-link'),cue=cell.querySelector('.ss-extreme-link-cue'),
              figure=cell.querySelector('.ss-extreme-number'),range=document.createRange();range.selectNodeContents(figure);
            const ink=range.getBoundingClientRect(),box=cue.getBoundingClientRect();
            return Math.abs((box.left-ink.right)/scale-5)<=0.5&&Math.abs(box.width/scale-14)<=0.5&&
              Math.abs(box.height/scale-14)<=0.5&&figure.parentNode===cell&&figure===cell.firstChild&&
              figure.nextSibling===button&&!button.contains(figure)&&button.contains(cue)&&
              getComputedStyle(cell).display==='flex'&&getComputedStyle(cell).flexWrap==='nowrap';
          }),
          pairs:finance.every(host=>{
            const buttons=[...host.querySelectorAll('.ss-metric-battle-link')],box=host.getBoundingClientRect(),
              first=buttons[0].getBoundingClientRect(),last=buttons[1].getBoundingClientRect();
            return buttons.length===2&&Math.abs((last.left-first.right)/scale-3)<=0.5&&
              Math.abs((first.left-box.left)-(box.right-last.right))<=scale;
          })};
      },scale);
      check('Source arrows follow original figures by 5px and financial Min/Max stay adjacent at '+scale+': '+JSON.stringify(actions),
        actions.performance===6&&actions.finance===5&&actions.arrows&&actions.pairs);
      check('Metric coverage adds no repeated visible rows or counters at '+scale,table.coverage===0);
      await publish('credits_costs','max',{pending:true});
      check('One partial-results badge stays with the identity without repeated metric counters at '+scale,
        await page.locator('#ss-groups .ss-group').evaluate(card=>
          card.querySelectorAll('.ss-group-heading .ss-group-coverage').length===1&&
          card.querySelectorAll('.ss-cell-coverage,.ss-count-coverage,.ss-wn8-coverage').length===0));
      await publish('credits_costs','max',{noSources:true});
      check('Missing financial source references leave no empty extrema action slots at '+scale,
        await page.locator('#ss-groups .ss-group').evaluate(card=>card.querySelectorAll('.ss-credit-extreme-actions').length===0&&
          [...card.querySelectorAll('.ss-credit-cell')].every(cell=>{
            const content=[...cell.children].filter(child=>!child.classList.contains('ss-credit-inline-label'));
            return content.length===1&&content[0].classList.contains('ss-cell-value')&&
              [...cell.querySelectorAll('.ss-credit-inline-label')].every(label=>label.getAttribute('aria-hidden')==='true');
          })));
      for(const profile of [
        {name:'Long synthetic vehicle designation with complete metadata',width:590,count:1234567890123456},
        {name:'Long synthetic pending vehicle designation',width:590,empty:true},
      ]){
        await publish('credits_costs','max',profile);
        const result=await page.locator('#ss-groups .ss-group').evaluate((card,scale)=>{
          const box=node=>node.getBoundingClientRect(),header=box(card.querySelector('.ss-group-header')),stats=box(card.querySelector('.ss-group-stats')),
            identity=box(card.querySelector('.ss-group-name'));
          const kpis=[...card.querySelectorAll('.ss-group-kpi')].map(node=>{
            const owner=box(node),label=box(node.querySelector('.ss-kpi-label')),value=node.querySelector('.ss-kpi-value'),figure=box(value),range=document.createRange();range.selectNodeContents(value);
            return {labelTop:label.top,bottom:figure.bottom,text:value.textContent,
              lines:[...range.getClientRects()].filter(rect=>rect.width>0&&rect.height>0).length,
              fits:figure.left>=owner.left-scale&&figure.right<=owner.right+scale&&
                [...range.getClientRects()].every(rect=>rect.left>=figure.left-scale&&rect.right<=figure.right+scale)};
          });
          return {kpis,statsTop:stats.top,statsBottom:stats.bottom,headerHeight:header.height/scale,
            identityHeight:identity.height/scale,statsHeight:stats.height/scale,
            contentHeight:(Math.max(identity.bottom,stats.bottom)-header.top)/scale,
            contained:identity.left>=header.left-scale&&stats.right<=header.right+scale&&
              identity.top>=header.top-scale&&identity.bottom<=header.bottom+scale};
        },scale);
        check('Wrapped identities and multi-line figures retain top labels and aligned bottoms at '+scale+': '+JSON.stringify(result),
          result.contained&&result.kpis.length===3&&result.kpis.every(kpi=>kpi.fits&&Math.abs(kpi.labelTop-result.statsTop)<=scale&&Math.abs(kpi.bottom-result.statsBottom)<=scale)&&
          result.headerHeight<=result.contentHeight+3);
        if(profile.empty)check('A zero-results group retains its full recorded count and unknown values at '+scale,
          result.kpis[0].text==='137'&&result.kpis[1].text==='—'&&result.kpis[2].text==='—');
        else check('An actually wrapped count keeps every digit without a fixed reserved row at '+scale+': '+JSON.stringify(result),
          result.kpis[0].lines>1&&result.kpis[0].text.replace(/\s/g,'')===String(profile.count));
      }
      await require('./ui-sort-selected-cell.cjs')({page,scale,check});
    }finally{await page.close();}
  }
  await require('./ui-aggregate-responsive.cjs')({browser,nativeHost,check});
};
