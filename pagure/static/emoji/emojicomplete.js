emoji_complete = function(json_url, folder) {

  emojione.imagePathPNG = folder;
  emojione.imageType = 'png';
  emojione.sprites = true;

  var emojiStrategy;
  if (!emojiStrategy) {
    $.getJSON(
      json_url,
      function( data ) {
        emojiStrategy =  data;
      }
    );
  }

  $("textarea").textcomplete([ {
    match: /\B:([\-+\w]*)$/,
    search: function (term, callback) {
      var results = [];
      var results2 = [];
      var results3 = [];
      console.log(emojiStrategy);
      $.each(emojiStrategy,function(shortname,data) {
        if(shortname.indexOf(term) > -1) { results.push(shortname); }
        else {
          if((data.aliases !== null) && (data.aliases.indexOf(term) > -1)) {
            results2.push(shortname);
          }
          else if((data.keywords !== null) && (data.keywords.indexOf(term) > -1)) {
            results3.push(shortname);
          }
        }
      });

      if(term.length >= 3) {
        results.sort(function(a,b) { return (a.length > b.length); });
        results2.sort(function(a,b) { return (a.length > b.length); });
        results3.sort();
      }
      var newResults = results.concat(results2).concat(results3);

      callback(newResults);
    },
    template: function (shortname) {
      return '<span class="emojione-'+emojiStrategy[shortname].unicode+'" title=":rabbit:"></span>:'+shortname+':';
    },
    replace: function (shortname) {
      return ':'+shortname+': ';
    },
    index: 1,
    maxCount: 10
  }
  ],{
    footer: '<a href="http://www.emoji.codes" target="_blank">Browse All<span class="arrow">&raquo;</span></a>'
  });
};
