/* Compact aggregate statistics keep their width while the sort caption fits in full. */
const fs=require('fs'),path=require('path');
const frames=page=>page.evaluate(()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve))));
module.exports=async({browser,nativeHost,check})=>{
  const languages=JSON.parse(fs.readFileSync(path.join(__dirname,'../data/languages.json'),'utf8')).languages;
  for(const scale of [1,2]){
    const page=await nativeHost(browser,{initialViewport:{width:3840,height:2560},viewport:{width:3840,height:2560,scale}});
    let sequence=0;
    try{
      await page.evaluate(()=>{window.__aggregateResponsiveFixture=JSON.parse(model.payload);});
      async function publish(language,messages,width,options={}){
        await page.evaluate(({language,messages,width,scale,options,sequence})=>{
          const payload=JSON.parse(JSON.stringify(__aggregateResponsiveFixture)),scope=payload.scopes.launch;
          payload.account_key='synthetic-aggregate-responsive-'+scale+'-'+sequence;
          payload.viewport={width:3840,height:2560,scale};payload.window_size=[width,1100];
          payload.localization={language,messages};
          payload.appearance={window_settings:{background_transparency:0,maximized:false,restored_width:width,restored_height:1100}};
          if(options.base)payload.appearance.card_widths={maps:options.base};
          if(options.wide)payload.appearance.wide_card_widths={maps:options.wide};
          const item=JSON.parse(JSON.stringify(scope.maps[0])),stats=item.stats;
          item.id='synthetic-aggregate-responsive';item.name=options.longName?'Synthetic map with a deliberately extended translated name':'Synthetic map';
          stats.battles=123;stats.observed_battles=137;stats.win_rate=100;stats.wn8=3456;stats.wn8_count=123;
          stats.credits_net_received={count:120,min:-1234567,avg:-1234567,max:-1234567,sum:-148148040};
          stats.currencies.credits.net=-148148040;stats.currencies.credits.net_count=120;
          scope.maps=[item];scope.pagination.maps={page:0,pages:1,total:1,page_size:40};
          scope.ordering.maps={metric:'credits_net_received',statistic:'avg',direction:'desc',chronology:'newest'};
          scope.data_revision='aggregate-responsive-'+sequence;
          model.payload=JSON.stringify(payload);GRZSessionStats.update(payload);
          document.getElementById('ss-scope-launch').onclick();document.getElementById('ss-group-maps').onclick();
        },{language,messages,width,scale,options,sequence:++sequence});
        await frames(page);
      }
      async function geometry(){return page.locator('#ss-groups .ss-group').first().evaluate((card,scale)=>{
        const box=node=>{const r=node.getBoundingClientRect();return {left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale,width:r.width/scale,height:r.height/scale};};
        const inside=(a,b)=>a.left>=b.left-1&&a.right<=b.right+1&&a.top>=b.top-1&&a.bottom<=b.bottom+1;
        const rangeBoxes=node=>{const r=document.createRange();r.selectNodeContents(node);return [...r.getClientRects()].filter(r=>r.width>0&&r.height>0).map(r=>({left:r.left/scale,right:r.right/scale,top:r.top/scale,bottom:r.bottom/scale}));};
        const header=card.querySelector('.ss-group-header'),identity=card.querySelector('.ss-group-name'),stats=card.querySelector('.ss-group-stats');
        const kpis=[...card.querySelectorAll('.ss-group-kpi')].map(node=>box(node));
        const badge=card.querySelector('.ss-group-sort-value'),caption=badge.querySelector('.ss-group-sort-caption-text'),number=badge.querySelector('.ss-group-sort-number');
        const icon=badge.querySelector('.ss-sort-partial-icon'),captionLines=rangeBoxes(caption),lineTops=[];
        for(const line of captionLines)if(!lineTops.some(top=>Math.abs(top-line.top)<1))lineTops.push(line.top);
        const cardBox=box(card),headerBox=box(header),badgeBox=box(badge),captionBox=box(caption),numberBox=box(number),iconBox=icon&&box(icon);
        const performance=box(card.querySelector('.ss-performance')),economy=box(card.querySelector('.ss-economy'));
        const more=card.querySelector('.ss-map-more-button'),moreBox=more&&box(more);
        const group=box(document.getElementById('ss-groups'));
        return {card:cardBox,group,header:headerBox,identity:box(identity),stats:box(stats),kpis,badge:badgeBox,
          captionLines:lineTops.length,captionText:caption.textContent,captionFits:captionLines.length>0&&captionLines.every(line=>inside(line,captionBox)),
          badgeFits:[captionBox,numberBox,iconBox].filter(Boolean).every(part=>inside(part,badgeBox))&&rangeBoxes(number).every(line=>inside(line,numberBox)),
          partial:!!icon&&getComputedStyle(icon).backgroundImage.includes('img://gui/maps/icons/library/alertIcon.png'),
          headerFits:[box(identity),box(stats),...kpis,badgeBox].every(part=>inside(part,headerBox)),
          moreFits:!!more&&moreBox.width>=40&&moreBox.height>=20&&inside(moreBox,headerBox)&&rangeBoxes(more).every(line=>inside(line,moreBox)),
          tablesFit:inside(performance,cardBox)&&inside(economy,cardBox),performance,economy,
          two:document.getElementById('ss-groups').classList.contains('ss-two-columns')};
      },scale);}
      for(const [language,messages]of Object.entries(languages))for(const width of [550,863,1200,1600]){
        await publish(language,messages,width);const value=await geometry(),caption=language+'/'+scale+'x/'+width;
        check('Aggregate KPI columns keep compact 60/62/72 widths '+caption+': '+JSON.stringify(value.kpis),
          value.kpis.length===3&&value.kpis.every((box,index)=>Math.abs(box.width-[60,62,72][index])<=1)&&
          value.kpis.slice(1).every((box,index)=>box.left-value.kpis[index].right>=-1&&box.left-value.kpis[index].right<=8));
        check('The full sorting caption and warning remain on one contained line '+caption+': '+JSON.stringify({lines:value.captionLines,caption:value.captionText,badge:value.badge}),
          value.captionLines===1&&value.captionFits&&value.badgeFits&&value.partial&&value.headerFits&&value.moreFits&&value.tablesFit);
        if(width===863)check('Default single-column maps use the 720px cap and horizontal tables '+caption+': '+JSON.stringify(value),
          !value.two&&Math.abs(value.card.width-720)<=1&&value.economy.left>=value.performance.right-1&&Math.abs(value.economy.top-value.performance.top)<=1);
        if(width===550)check('Small aggregates separate identity from compact statistics and stack readable tables '+caption+': '+JSON.stringify(value),
          !value.two&&value.card.width<=value.group.width+1&&value.identity.bottom<=value.stats.top+1&&value.economy.top>=value.performance.bottom-1);
      }
      for(const options of [{base:600},{wide:800},{longName:true}]){
        await publish('pl',languages.pl,863,options);const value=await geometry();
        const expected=options.base||options.wide||720;
        check('Single-column aggregate sizing respects its configured preset '+scale+'x/'+JSON.stringify(options)+': '+JSON.stringify(value),
          !value.two&&Math.abs(value.card.width-expected)<=1&&value.headerFits&&value.moreFits&&value.tablesFit&&value.captionLines===1&&value.badgeFits);
      }
    }finally{await page.close();}
  }
};
