AWS.config.region = 'us-west-2'; // Region
AWSCognito.config.region = 'us-west-2';
     
var poolData = {
    UserPoolId : 'us-west-2_rg9HX38jD',
    ClientId : '6n3ua26911atsluvne0ifja3ns'
};
var userPool = new AWSCognito.CognitoIdentityServiceProvider.CognitoUserPool(poolData);
AWS.config.credentials = new AWS.CognitoIdentityCredentials({
    IdentityPoolId: 'us-west-2:621ae3f6-3169-4ebd-8431-00bfd332fb03'
});
 
AWS.config.credentials.get(function(err){
    if (err) {
        alert(err);
    }
});

var dynamodb = new AWS.DynamoDB();
var datumVal = new Date() - 86400000;
var params = { 
                TableName: 'wine-cellar-monitor',
                KeyConditionExpression: '#id = :iottopic and #ts >= :datum',
                ExpressionAttributeNames: {
                    "#id": "id",
                    "#ts": "timestamp"
                },
                ExpressionAttributeValues: {
                    ":iottopic": { "S" : "temp-humidity/Omega-F4E1/bottom"},
                    ":datum": { "N" : datumVal.toString()}
                }
             };
/* Create the context for applying the chart to the HTML canvas */
var tctx = $("#temperaturegraph").get(0).getContext("2d");
var hctx = $("#humiditygraph").get(0).getContext("2d");

/* Set the options for our chart */
var options = { 
                responsive: true,
                showLines: true,
                scales: {
                    xAxes: [{
                        display: true
                    }],
                    yAxes: [{
                        ticks: {
                            beginAtZero:true
                        }
                    }]
                } 
              };

/* Set the inital data */
var tinit = {
    labels: [],
    datasets: [
        {
            label: "Temperature °C",
            backgroundColor: 'rgba(204,229,255,0.5)',
            borderColor: 'rgba(153,204,255,0.75)',
            data: []
        }
    ]
};
var hinit = {
  labels: [],
  datasets: [
        {
            label: "Humidity %",
            backgroundColor: 'rgba(229,204,255,0.5)',
            borderColor: 'rgba(204,153,255,0.75)',
            data: []
        }
  ]
};
var temperaturegraph = new Chart.Line(tctx, {data: tinit, options: options});
var humiditygraph = new Chart.Line(hctx, {data: hinit, options: options});
$(function() {
  getData();
  $.ajaxSetup({ cache: false });
  setInterval(getData, 300000);
});

/* Makes a scan of the DynamoDB table to set a data object for the chart */
function getData() {
    dynamodb.query(params, function(err, data) {
        if (err) {
            console.log(err);
            return null;
        } 
        else {
            // placeholders for the data arrays
            var compositeData = [];
            var temperatureValues = [];
            var humidityValues = [];
            var labelValues = [];
            
            // placeholders for the data read
            var temperatureRead = 0.0;
            var humidityRead = 0.0;
            var timestamp = 0.0;
            var timeRead = "";

            // placeholders for the high/low markers
            var temperatureHigh = -999.0;
            var humidityHigh = -999.0;
            var temperatureLow = 999.0;
            var humidityLow = 999.0;
            var temperatureHighTime = "";
            var temperatureLowTime = "";
            var humidityHighTime = "";
            var humidityLowTime = "";

            for (var i in data['Items']) {
                // read the values from the dynamodb JSON packet
                temperatureRead = parseFloat(data['Items'][i]['payload']['M']['temperature']['N']);
                humidityRead = parseFloat(data['Items'][i]['payload']['M']['humidity']['N']);

                timestamp = parseFloat(data['Items'][i]['payload']['M']['timestamp']['N']);
                timeRead = new Date(timestamp * 1000.)

                // check the read values for high/low watermarks
                if (temperatureRead < temperatureLow) {
                    temperatureLow = temperatureRead;
                    temperatureLowTime = timeRead;
                }
                if (temperatureRead > temperatureHigh) {
                    temperatureHigh = temperatureRead;
                    temperatureHighTime = timeRead;
                }
                if (humidityRead < humidityLow) {
                    humidityLow = humidityRead;
                    humidityLowTime = timeRead;
                }
                if (humidityRead > humidityHigh) {
                    humidityHigh = humidityRead;
                    humidityHighTime = timeRead;
                }

                // append the read data to the data arrays
                compositeData.push([timestamp, temperatureRead, humidityRead]);
            }

            // Sort data by time
            compositeData.sort(function(a, b){return a[0] - b[0]});

            // Remove duplicates and break into separate arrays
            var lastTimestamp = 0.0
            for (var i = 0; i < compositeData.length; i++) {
                if (i === 0 || ((i > 0) && (compositeData[i][0] !== lastTimestamp))) {
                    labelValues.push(new Date(compositeData[i][0] * 1000.));
                    temperatureValues.push(compositeData[i][1]);
                    humidityValues.push(compositeData[i][2]);
                    lastTimestamp = compositeData[i][0];
                }
            }

            // set the chart object data and label arrays
            temperaturegraph.data.labels = labelValues;
            temperaturegraph.data.datasets[0].data = temperatureValues;
            humiditygraph.data.labels = labelValues;
            humiditygraph.data.datasets[0].data = humidityValues;

            // redraw the graph canvas
            temperaturegraph.update();
            humiditygraph.update();

            // update the high/low watermark sections
            $('#t-high').text(Number(temperatureHigh).toFixed(2).toString() + '°C at ' + temperatureHighTime);
            $('#t-low').text(Number(temperatureLow).toFixed(2).toString() + '°C at ' + temperatureLowTime);
            $('#h-high').text(Number(humidityHigh).toFixed(2).toString() + '% at ' + humidityHighTime);
            $('#h-low').text(Number(humidityLow).toFixed(2).toString() + '% at ' + humidityLowTime);
        }
    });
}