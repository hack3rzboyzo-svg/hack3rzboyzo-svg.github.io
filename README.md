<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>JJTHEANIMATOR</title>

<style>
body{
    margin:0;
    font-family:Arial, Helvetica, sans-serif;
    background:#111;
    color:white;
}

header{
    background:linear-gradient(90deg,#ff0000,#ff6600);
    padding:30px;
    text-align:center;
}

header h1{
    margin:0;
    font-size:40px;
}

.container{
    max-width:1000px;
    margin:auto;
    padding:20px;
}

.channel-box{
    background:#1e1e1e;
    padding:20px;
    border-radius:10px;
    text-align:center;
}

.subscribe{
    margin-top:15px;
    display:inline-block;
    background:red;
    padding:12px 20px;
    border-radius:6px;
    color:white;
    text-decoration:none;
    font-weight:bold;
}

.video{
    margin-top:30px;
    text-align:center;
}

iframe{
    width:100%;
    height:500px;
    border:none;
    border-radius:10px;
}

footer{
    text-align:center;
    padding:20px;
    margin-top:40px;
    background:#000;
    color:#aaa;
}

/* 🎮 GAMES SECTION */
.games{
    margin-top:40px;
    text-align:center;
}

.game-list{
    display:flex;
    gap:20px;
    justify-content:center;
    flex-wrap:wrap;
}

.game-card{
    background:#1e1e1e;
    padding:20px;
    border-radius:10px;
    width:300px;
}

.game-card iframe{
    width:100%;
    height:300px;
    margin-top:10px;
}

.game-card a{
    display:inline-block;
    margin:10px;
    padding:8px 12px;
    background:#ff4444;
    color:white;
    text-decoration:none;
    border-radius:5px;
}
</style>
</head>

<body>

<header>
<h1>JJTHEANIMATOR</h1>
<p>Animating • Funny Videos • Content Creation • Blender</p>
</header>

<div class="container">

<div class="channel-box">
<h2>Visit the Channel</h2>
<a href="https://www.youtube.com/@JIJTHETUBER" target="_blank">
youtube.com/@JIJTHETUBER
</a>

<br><br>

<a class="subscribe" href="https://www.youtube.com/@JIJTHETUBER?sub_confirmation=1" target="_blank">
Subscribe on YouTube
</a>
</div>

<div class="video">
<h2>Featured Video</h2>

<iframe 
src="https://www.youtube.com/embed/YsYrBoKo1wE"
allowfullscreen>
</iframe>

</div>

<!-- 🎮 GAMES SECTION (NOW INSIDE BODY ✅) -->
<section class="games">
<h2>🎮 Games I Coded While Bored</h2>

<div class="game-list">

<div class="game-card">
<h3>Snake Game 🐍</h3>
<p>Play it right here!</p>
<iframe src="snake.html"></iframe>
<a href="snake.html" download>⬇ Download</a>
</div>

<div class="game-card">
<h3>Number Guess 🔢</h3>
<p>Try to guess the number!</p>
<a href="https://replit.com" target="_blank">▶ Play</a>
</div>

</div>
</section>

</div>

<footer>
<p>Fan Website for JIJTHETUBER</p>
</footer>

</body>
</html>
