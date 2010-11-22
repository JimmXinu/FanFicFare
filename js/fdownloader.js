var g_CurrentKey = null;
var g_Counter = 0;

var COUNTER_MAX = 50;


function setErrorState(error)
{
	olderr = error;
	error = error + "<br/><a href='mailto:sigizmund@gmail.com?subject=Problem with the fanfiction downloader'>" + "Complain about this error</a>";
	$('#error').html(error);
}

function clearErrorState()
{
	$('#error').html('');
}

function showFile(data)
{
	$('#yourfile').html('<a href="/file?id=' + data.key + '">' + data.name + " by " + data.author + "</a>");
	$('#yourfile').show();
}

function hideFile()
{
	$('#yourfile').hide();
}

function checkResults()
{
	if ( g_Counter >= COUNTER_MAX )
	{
		return;
	}
	
	g_Counter+=1;

	$.getJSON('/progress', { 'key' : g_CurrentKey }, function(data)
	{
		if ( data.result != "Nope")
		{
			if ( data.result != "OK" )
			{
				leaveLoadingState();
				setErrorState(data.result);
			}
			else
			{
				showFile(data);
				leaveLoadingState();
				// result = data.split("|");
				// showFile(result[1], result[2], result[3]);
			}
			
			$("#progressbar").progressbar('destroy');
			g_Counter = 101;
		}
	});
	
	if ( g_Counter < COUNTER_MAX ) 
		setTimeout("checkResults()", 1000);
	else
	{
		leaveLoadingState();
		setErrorState("Operation takes too long - terminating by timeout (story too long?)");
	}
}

function enterLoadingState()
{
	$('#submit_button').hide();
	$('#ajax_loader').show();
}

function leaveLoadingState()
{
	$('#submit_button').show();
	$('#ajax_loader').hide();
}

function downloadFanfic()
{
	clearErrorState();
	hideFile();


	format = $("#format").val();
	alert(format);
	
	return;
	
	var url = $('#url').val();
	var login = $('#login').val();
	var password = $('#password').val();
	
	if ( url == '' )
	{
		setErrorState('URL shouldn\'t be empty');
		return;
	}
	
	if ( (url.indexOf('fanfiction.net') == -1 && url.indexOf('fanficauthors') == -1 && url.indexOf('ficwad') == -1  &&  url.indexOf('fictionpress') == -1) || (url.indexOf('adultfanfiction.net') != -1) )
	{
		setErrorState("This source is not yet supported. Ping me if you want it!");
		return;
	}
	
	$.post('/submitDownload', {'url' : url, 'login' : login, 'password' : password, 'format' : format}, function(data)
	{
		g_CurrentKey = data;
		g_Counter = 0;
		setTimeout("checkResults()", 1000);
		enterLoadingState();
	})
}