window.chartColors = {
  red: 'rgb(255, 20, 100)',
  orange: 'rgb(255, 159, 64)',
  yellow: 'rgb(255, 205, 86)',
  green: 'rgb(75, 192, 192)',
  blue: 'rgb(54, 162, 235)',
  purple: 'rgb(153, 102, 255)',
  grey: 'rgb(201, 203, 207)'
};


function issues_history_stats_plot(data) {
  $("#commiter_list").hide();
  $(".commit_trend").hide();
  var color = Chart.helpers.color;

  var _open_tickets = [];
  var _close_tickets = [];
  var _total = []
  var _lbl = []
  for (var _d in data.stats) {
    _lbl.push(_d.split('T', 1)[0]);
    _open_tickets.push(data.stats[_d].open_ticket);
    _close_tickets.push(data.stats[_d].closed_ticket);
    _total.push(data.stats[_d].count);
  }

  var barChartData = {
    labels: _lbl,
    datasets: [{
      label: 'Tickets opened that week',
      backgroundColor: color(window.chartColors.blue).alpha(0.5).rgbString(),
      borderColor: window.chartColors.blue,
      borderWidth: 1,
      data: _open_tickets
    }, {
      label: 'Tickets closed that week',
      backgroundColor: color(window.chartColors.red).alpha(0.5).rgbString(),
      borderColor: window.chartColors.red,
      borderWidth: 1,
      data: _close_tickets
    }]
  };

  var lineData = {
    labels: _lbl,
    datasets: [{
      label: 'Tickets open (total)',
      backgroundColor: color(window.chartColors.blue).alpha(0.5).rgbString(),
      borderColor: window.chartColors.blue,
      borderWidth: 1,
      pointRadius: 0,
      data: _total
    }]
  };

  new Chart('total_issue_trend_graph', {
    type: 'line',
    data: lineData,
    options: {
      scales: {
        yAxes: [{
          stacked: true
        }]
      },
      plugins: {
        filler: {
          propagate: true
        },
      },
      title: {
        display: true,
        text: 'Evolution of the number of open tickets over the last year'
      }
    }
  });

  new Chart("issue_trend_graph", {
    type: 'bar',
    data: barChartData,
    options: {
      responsive: true,
      legend: {
        position: 'top',
      },
      title: {
        display: true,
        text: 'Tickets opened and closed per week'
      }
    }
  });

  $("#data_stats_spinner").hide();
  $(".issue_trend").show();
}

function show_commits_authors(data) {
  $(".commit_trend").hide();
  $(".issue_trend").hide();
  var _b = $("#commiter_list");
  var html = '<h2>Authors stats</h2><p> Since '
    + new Date(data.results[3]*1000) + ' there has been '
    + data.results[0] + ' commits found in this repo, from '
    + data.results[2] + ' contributors</p>\n'
    + '<div class="list-group">\n';
  for (const key in data.results[1]){
    const cnt = data.results[1][key][0];
    for (let entry in data.results[1][key][1]){
      entry = data.results[1][key][1][entry];
      html += '  <a class="list-group-item" href="'
        + view_commits_url.replace('---', entry[1]) + '">'
        + '<img class="avatar circle" src="' + entry[2] + '"/> '
        + entry[0]
        + '<div class="pull-xs-right">' + cnt + ' commits</div>'
        + '</a>\n';
    }
  }
  html += '</div>';
  _b.html(html);
  $("#data_stats_spinner").hide();
  _b.show();
}

function show_commits_history(data) {
  $("#commiter_list").hide();
  $(".issue_trend").hide();

  var color = Chart.helpers.color;

  var _data = [];
  var _lbl = []
  for (var _d in data.results) {
    _lbl.push(data.results[_d][0]);
    _data.push(data.results[_d][1]);
  }

  var data = {
    labels: _lbl,
    datasets: [{
      label: 'Number of commits per week',
      backgroundColor: color(window.chartColors.blue).alpha(0.5).rgbString(),
      borderColor: window.chartColors.blue,
      borderWidth: 1,
      pointRadius: 0,
      data: _data
    }]
  };

  var options = {
    scales: {
      yAxes: [{
        stacked: true
      }]
    },
    plugins: {
      filler: {
        propagate: true
      },
    },
    title: {
      display: true,
      text: 'Evolution of the number of commits over the last year'
    }
  };

  var chart = new Chart('commit_trend_graph', {
    type: 'line',
    data: data,
    options: options
  });

  $("#data_stats_spinner").hide();
  $(".commit_trend").show();
}

function process_async(url, _data, callback) {
  $.post(url, _data)
  .done(function(data) {
    wait_for_task(data.url, callback);
  })
}

function wait_for_task(url, callback) {
  $.get(url)
  .done(function(data){
    callback(data);
    $("#data_stats_spinner").hide();
  })
  .fail(function(){
    window.setTimeout(function() {wait_for_task(url, callback);}, 1000);
  });
}
