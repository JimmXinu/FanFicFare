_part1 = """
  <body class="StoryPage" id="StoryPage">
  <nav class="navigation navigation_white">
    <div class="navigation__left">
    <a class="navigation__brand navigation__brand_dark" href="/" target="_self" title="Inkitt - Free Books, Stories and Novels">
      <svg viewBox="0 0 423.5 134.29" xmlns="http://www.w3.org/2000/svg">
      <g>
        <path d="M68.37,16.5c1-2.43,3.1-8.6-3.6-16.4-5.9,8.35-14.48,8.22-23.15,8.09l-21.9,0C11.39,8.18,4.57,11.11,1,19.31c-3.65,8.43,3.59,16.39,3.59,16.39,5.9-8.35,14.49-8.22,23.15-8.08.64,0,5.07,0,14.33,0,0,0-4,0,7.58-.07C58,27.56,65,24.78,68.37,16.5Z"></path>
        <path d="M77.43,118.66c2.16-2.23,4.91-19.57-.42-20.09-2.18,13.23-15.46,16.28-18.21,16.34-3.11.07-15.47.05-17.18,0-9-.14-10.13-.26-21.9-.23-8.33,0-15.14,2.88-18.69,11.08a12.91,12.91,0,0,0-.6,8.32l41.67,0S61.31,135.31,77.43,118.66Z"></path>
        <path d="M93.32,45.28c-10.11-1.89-17.18,3.29-24,10.21C75.69,60.18,77,66.41,77,73.3c0,1.1,0,31.16,0,32.21,0,3.08-.51,13.55-.51,13.55,7.41,18.27,22.8,19.68,34.29,6a24.56,24.56,0,0,1-6.22-14.94c-.13-2.67-.15-4.81-.15-5.06,0-3.95,0-26.52,0-26.78a8.7,8.7,0,0,1,.51-2.56c2.32-4.78,11-9,11-9a13.92,13.92,0,0,1,8.63-1.86c4.49.62,6.11,3.31,6.16,7.39h0c0,13,0,21,0,34,0,1.82,0,3.64,0,5.46.22,18.16,9.58,26,26.9,21.18,7.94-2.19,15.13-6.74,22.82-10.19,8.16,15,24.15,15.64,34.11.52-7.95-7.45-7.62-12-7.85-30.55,5.84-.79,12,1.09,15,6a60.46,60.46,0,0,1,6.84,16.11c4.28,16.44,14.45,22.86,30.09,17.87,7.2-2.29,20.9-9.37,21.07-9.46,2.91,9,10.32,11.61,19.37,11,10.68-.71,28.81-12.82,32.44-15.87l0-25c0,10.67-5.58,18-16,20.87-5.72,1.57-9.23-.83-9.87-6.85-.17-1.57,0-48.32,0-50.64,0-12.79-9.45-18.23-20.3-15.63-6.25,1.5-11.62,4.65-15.18,10.65,6.53,2.7,8.1,9.1,8.1,15.16,0,12.29,0,22.12,0,34.41a13.54,13.54,0,0,1-14.59,13.63c-5-.5-5.4-4.51-5.59-7-1.51-18.83-8.85-23.27-22.76-24.22-.32,0,8.54-6.13,13.91-15.54,5-8.8,3.13-21.57-3.26-27.17-5.45-4.78-15.17-4.3-24.15,1.67-4.82,3.21-9.21,7.07-14.9,11.48,0,0,.11-16.14,0-25.11-.14-8.67-.26-17.25,8.08-23.15-7.8-6.69-15.65-7.24-24.09-3.6-8.2,3.55-11.14,10.36-11.16,18.69-.07,27.77.05,52.66,0,80.43,0,6.43-7.41,13.11-14.46,13.19-5.51.07-7.23-2.74-7.25-12,0-15.25.25-25-.13-40.23h-.06c0-6.26-2.2-12.39-6.13-15.83-5.45-4.78-15.17-4.3-24.14,1.68-4.82,3.21-9.21,7.07-14.9,11.48l-8.25,6.46C104.59,50.83,100,46.53,93.32,45.28ZM206.93,61.89c.09-3.6,6.57-6.85,11.86-6.12,4.83.66,6.28,3.86,5.89,8.31-.66,7.65-7.75,17-17.81,22.4C206.87,77.68,206.74,69.79,206.93,61.89Z"></path>
        <circle cx="292.47" cy="14.42" r="14.42"></circle>
        <path d="M346.27,2.38C337.84-1.27,330-.72,322.19,6c8.35,5.9,8.22,14.49,8.08,23.15-.07,4.38-.14,85.05-.14,87.58a27.79,27.79,0,0,0,1.45,6.82c2.92,9,10.32,11.19,19.38,10.58,10.67-.71,19.53-5.54,27.73-12,1.47-1.15,3-2.23,4.71-3.49l0-25c0,10.67-5.58,18-16,20.87-5.72,1.57-9.23-.82-9.87-6.85-.17-1.57-.12-86.61-.12-86.61C357.33,12.74,354.48,5.93,346.27,2.38Z"></path>
        <path d="M405.85,21.07c0-8.33-2.88-15.14-11.08-18.69C386.33-1.27,378.47-.72,370.68,6c8.35,5.9,8.22,14.49,8.09,23.15-.07,4.38-.14,85.05-.14,87.58a27.79,27.79,0,0,0,1.45,6.82c2.91,9,10.32,11.19,19.38,10.58A42.81,42.81,0,0,0,416.8,129c6.62-3.53,7.71-12.59,5.94-17.45a25.38,25.38,0,0,1-6.91,3c-5.72,1.57-9.36-.82-10-6.85C405.66,106.11,405.88,34.09,405.85,21.07Z"></path>
        <path d="M51.38,18c0-8.33-26.95-.61-27.08,8.06-.07,4.37-.14,88.09-.14,90.62a27.74,27.74,0,0,0,1.46,6.82c2.91,9,10.32,11.19,19.37,10.58,10.67-.71,19.53-5.54,27.73-12,1.47-1.15,3-2.23,4.71-3.49l0-25c0,10.67-5.58,18-16,20.87-5.72,1.57-9.22-.82-9.87-6.85C51.33,106.11,51.42,31.06,51.38,18Z"></path>
        <path d="M422.35,48.67c1-2.43,3.1-8.6-3.59-16.4-5.9,8.35-14.48,8.22-23.16,8.09l-63.05,0c-8.33,0-15.14,2.95-18.69,11.15-3.65,8.43,3.59,16.4,3.59,16.4,5.9-8.35,14.49-8.22,23.15-8.09l55.47,0s-4,0,7.58-.07C412,59.73,419,56.95,422.35,48.67Z"></path>
      </g>
      </svg>
    </a>
    <div class="navigation-group navigation-group_mobile js-navigation-mobile-menu">
      <div class="search js-search search_fullwidth">
      <button class="search__expander navigation-hoverable" data-track-source="Search Bar">
        <span class="search__icon">
        <svg height="19px" width="20px" xmlns="http://www.w3.org/2000/svg">
          <path d="M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14" fill-rule="evenodd"></path>
        </svg>
        </span>Search </button>
      <form class="js-search-form">
        <div class="search__inputWrapper">
        <span class="search__icon">
          <svg height="19px" width="20px" xmlns="http://www.w3.org/2000/svg">
          <path d="M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14" fill-rule="evenodd"></path>
          </svg>
        </span>
        <input class="search__input" name="search" placeholder="Type a phrase to search...">
        <button class="search__submit" type="submit">Search</button>
        </div>
      </form>
      </div>
      <ul class="navigation-list navigation-list_dark">
      <li class="navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable">
        <span class="navigation-list__title navigation-hoverable">Free Books</span>
        <div class="navigation-dropdown navigation-dropdown_fullwidth">
        <div class="stories-dropdown">
          <div class="stories-dropdown__col">
          <div class="stories-dropdown-title">Genres</div>
          <ul class="stories-dropdown-list">
            <li class="stories-dropdown-list__item">
            <a alt="Read Sci-Fi Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-scifi" href="/genres/scifi" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-scifi"></div>Sci-Fi
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Fantasy Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-fantasy" href="/genres/fantasy" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-fantasy"></div>Fantasy
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Adventure Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-adventure" href="/genres/adventure" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-adventure"></div>Adventure
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Mystery Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-mystery" href="/genres/mystery" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-mystery"></div>Mystery
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Action Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-action" href="/genres/action" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-action"></div>Action
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Horror Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-horror" href="/genres/horror" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-horror"></div>Horror
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Humor Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-humor" href="/genres/humor" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-humor"></div>Humor
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Erotica Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-erotica" href="/genres/erotica" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-erotica"></div>Erotica
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Poetry Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-poetry" href="/genres/poetry" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-poetry"></div>Poetry
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Other Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-other" href="/genres/other" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-other"></div>Other
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Thriller Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-thriller" href="/genres/thriller" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-thriller"></div>Thriller
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Romance Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-romance" href="/genres/romance" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-romance"></div>Romance
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Children Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-children" href="/genres/children" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-children"></div>Children
            </a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Read Drama Stories for Free" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="genre-drama" href="/genres/drama" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_genre-drama"></div>Drama
            </a>
            </li>
          </ul>
          </div>
          <div class="stories-dropdown__col">
          <div class="stories-dropdown-title">Fanfiction <a class="stories-dropdown-title__more" data-track-event="navbar-link-clicked" data-track-link="more fandoms" href="/fanfiction" target="_self">More Fanfiction</a>
          </div>
          <ul class="stories-dropdown-list">
            <li class="stories-dropdown-list__item stories-dropdown-list__item_fullwidth">
            <a alt="Harry Potter" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="fandom harry potter" href="/fanfiction?fandom_name=Harry+Potter&amp;fandom=Harry Potter" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_fandom-harry-potter"></div>Harry Potter
            </a>
            </li>
            <li class="stories-dropdown-list__item stories-dropdown-list__item_fullwidth">
            <a alt="Naruto" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="fandom naruto" href="/fanfiction?fandom_name=Naruto&amp;fandom=Naruto" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_fandom-naruto"></div>Naruto
            </a>
            </li>
            <li class="stories-dropdown-list__item stories-dropdown-list__item_fullwidth">
            <a alt="Supernatural" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="fandom supernatural" href="/fanfiction?fandom_name=Supernatural&amp;fandom=Supernatural" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_fandom-supernatural"></div>Supernatural
            </a>
            </li>
            <li class="stories-dropdown-list__item stories-dropdown-list__item_fullwidth">
            <a alt="Glee" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="fandom glee" href="/fanfiction?fandom_name=Glee&amp;fandom=Glee" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_fandom-glee"></div>Glee
            </a>
            </li>
            <li class="stories-dropdown-list__item stories-dropdown-list__item_fullwidth">
            <a alt="Lord of the rings" class="stories-dropdown-item stories-dropdown-item_simple" data-track-event="navbar-link-clicked" data-track-link="fandom the lord of the rings" href="/fanfiction?fandom_name=Lord+of+the+rings&amp;fandom=Lord of the rings" target="_self">
              <div class="stories-dropdown-item__icon stories-dropdown-item__icon_fandom-lotr"></div>Lord of the rings
            </a>
            </li>
          </ul>
          </div>
          <div class="stories-dropdown__col">
          <div class="stories-dropdown-title">Trending Topics</div>
          <ul class="stories-dropdown-list">
            <li class="stories-dropdown-list__item">
            <a alt="Love" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic love" href="/topics/love" target="_self">Love</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Magic" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic magic" href="/topics/magic" target="_self">Magic</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Werewolf" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic werewolf" href="/topics/werewolf" target="_self">Werewolf</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Family" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic family" href="/topics/family" target="_self">Family</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Friendship" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic friendship" href="/topics/friendship" target="_self">Friendship</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Death" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic death" href="/topics/death" target="_self">Death</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Supernatural" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic supernatural" href="/topics/supernatural" target="_self">Supernatural</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Mafia" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic mafia" href="/topics/mafia" target="_self">Mafia</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Fanfiction" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic fanfiction" href="/topics/fanfiction" target="_self">Fanfiction</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Alpha" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic alpha" href="/topics/alpha" target="_self">Alpha</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Short Story" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic short story" href="/topics/short-story" target="_self">Short Story</a>
            </li>
            <li class="stories-dropdown-list__item">
            <a alt="Indian Love Story" class="stories-dropdown-item stories-dropdown-item_hashtag" data-track-event="navbar-link-clicked" data-track-link="topic indian love story" href="/topics/indian-love-story" target="_self">Indian Love Story</a>
            </li>
          </ul>
          </div>
        </div>
        </div>
      </li>
      <li class="navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable" id="navigation-list__item-become_a_writer">
        <span class="navigation-list__title navigation-hoverable">Write</span>
        <ul class="navigation-dropdown">
        <div class="write-story">
          <button class="write-story__button" id="manage-stories-modal">
          <span class="write-story__icon">
            <svg height="21px" width="22px" xmlns="http://www.w3.org/2000/svg">
            <path d="M4.065 17.823c.159-.147.318-.293.475-.441 1.774-1.66 3.546-3.323 5.323-4.98a.47.47 0 0 1 .285-.125c2.108-.007 4.215-.005 6.322-.004.028 0 .055.013.147.036-.218.24-.395.473-.612.664-2.917 2.558-6.315 4.165-10.227 4.747-.55.083-1.109.122-1.663.18l-.05-.077zm11.233-10.57L22 .817c-.11.647-.194 1.267-.32 1.88a21.7 21.7 0 0 1-1.378 4.267c-.091.208-.19.295-.44.293-1.424-.013-2.848-.006-4.272-.006h-.292zm-8.693 6.484V10.93c0-.918-.01-1.836.008-2.754a.89.89 0 0 1 .187-.527c.61-.717 1.245-1.417 1.875-2.119.19-.21.393-.408.648-.67.013.16.023.231.024.303 0 1.904.003 3.809-.005 5.713 0 .131-.047.298-.138.387-.81.797-1.633 1.58-2.454 2.367-.027.026-.061.046-.145.108zM19.5 8.555c-.281.414-.539.82-.826 1.205-.307.413-.636.813-.971 1.205a.494.494 0 0 1-.325.163c-2.046.01-4.093.006-6.14.004-.028 0-.058-.01-.127-.025.07-.076.12-.141.18-.196.817-.75 1.633-1.501 2.456-2.245a.526.526 0 0 1 .31-.143c1.77-.008 3.542-.005 5.314-.004.027 0 .054.015.13.036zM5.437 9.895c0 1.326-.056 2.656.02 3.979.048.822-.166 1.432-.84 1.946-.467.356-.858.804-1.284 1.21-.013.013-.033.02-.105.059.26-2.555.877-4.968 2.209-7.194zm-2.119 8.732L.844 21 0 20.309l2.48-2.373.838.69zM21.004.067l-10.487 9.944v-.326c0-1.836.004-3.673-.007-5.51-.001-.224.08-.351.26-.478C13.415 1.853 16.324.62 19.568.155c.467-.067.938-.104 1.408-.155l.03.068z" fill-rule="evenodd"></path>
            </svg>
          </span>Write or Upload Story </button>
        </div>
        <ul class="navigation-dropdown__sublist">
          <li class="navigation-dropdown__item">
          <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="writers bootcamp" href="/writers-bootcamp" id="navigation-dropdown__link-writers_bootcamp" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">Novel Writing Boot Camp</div>
            <div class="navigation-dropdown__subtitle">The fundamentals of fiction writing by Bryan Thomas Schmidt</div>
          </a>
          </li>
          <li class="navigation-dropdown__item">
          <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="winners" href="/inkitt-winners" id="" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">Winners</div>
            <div class="navigation-dropdown__subtitle">Contest Winners</div>
          </a>
          </li>
          <li class="navigation-dropdown__item">
          <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="writers blog" href="/writersblog/" id="" target="_blank">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">The Writer&#39;s Blog</div>
            <div class="navigation-dropdown__subtitle">Learn about the craft of writing</div>
          </a>
          </li>
        </ul>
        </ul>
      </li>
      <li class="navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable">
        <span class="navigation-list__title navigation-hoverable">Community</span>
        <ul class="navigation-dropdown">
        <div class="navigation-contests">
          <div class="stories-dropdown-title">Featured Groups</div>
          <ul class="stories-dropdown-list">
          <li class="stories-dropdown-list__item stories-dropdown-list__item_fullwidth">
            <a class="stories-dropdown-item" data-track-event="navbar-link-clicked" data-track-link="/groups/Community" href="/groups/Community" target="_self">
            <img class="stories-dropdown-item__icon" loading="lazy" src="https://cdn-gcs.inkitt.com/uploads/group_category/1006/8df533eb-fb78-4000-88c3-3ba18aedcfe8.jpg">
            <div class="stories-dropdown-item__info">Inkitt Community <div class="stories-dropdown-item__footer">Welcome to Inkitt!</div>
            </div>
            </a>
          </li>
          </ul>
        </div>
        <ul class="navigation-dropdown__sublist">
          <li class="navigation-dropdown__item">
          <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="groups" href="/groups" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">Groups</div>
            <div class="navigation-dropdown__subtitle">Engage with fellow authors &amp; writers</div>
          </a>
          </li>
          <li class="navigation-dropdown__item">
          <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="guidelines" href="/guidelines" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">Community Guidelines</div>
            <div class="navigation-dropdown__subtitle">Discover the values of our community</div>
          </a>
          </li>
        </ul>
        </ul>
      </li>
      <li class="navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable">
        <a class="navigation-list__title navigation-hoverable" data-track-event="navbar-link-clicked" data-track-link="book-store" href="https://galatea.com" target="_blank">Galatea</a>
      </li>
      <li class="navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable">
        <span class="navigation-list__title navigation-hoverable">Writing Contests</span>
        <ul class="navigation-dropdown">
        <ul class="navigation-dropdown__sublist navigation-dropdown__contests">
          <li class="navigation-dropdown__item">
          <a class="contest-dropdown-item navigation-dropdown__link" href="/historical-romance-2024" target="_self">
            <img class="stories-dropdown-item__icon" src="https://cdn-gcs.inkitt.com/contestpictures/539c6e6a-ddd8-4d0b-a5fc-3f20e1a148b8.png">
            <div class="stories-dropdown-item__info">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">Historical Romance: Love Through the Ages</div>
            <div class="navigation-dropdown__subtitle">Romance Contest</div>
            </div>
          </a>
          </li>
          <li class="navigation-dropdown__item">
          <a class="contest-dropdown-item navigation-dropdown__link" href="/fantasy-worlds-2024" target="_self">
            <img class="stories-dropdown-item__icon" src="https://cdn-gcs.inkitt.com/contestpictures/eb4f6e87-1f46-4b85-9b67-a1abec95edf8.png">
            <div class="stories-dropdown-item__info">
            <div class="navigation-dropdown__title navigation-dropdown__title_bold">Fantasy Worlds: Beyond Imagination</div>
            <div class="navigation-dropdown__subtitle">Fantasy Contest</div>
            </div>
          </a>
          </li>
        </ul>
        </ul>
      </li>
      <li class="navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable">
        <a class="navigation-list__title navigation-hoverable" data-track-event="navbar-link-clicked" data-track-link="/author-subscription" href="/author-subscription" target="_self">Author Subscription</a>
      </li>
      </ul>
    </div>
    </div>
    <div class="navigation__right">
    <div class="navigation-group">
      <ul class="navigation-list navigation-actions navigation-list_dark">
      <li class="navigation-actions__item navigation-show_desktop">
        <div class="search js-search">
        <button class="search__expander navigation-hoverable" data-track-source="Search Bar">
          <span class="search__icon">
          <svg height="19px" width="20px" xmlns="http://www.w3.org/2000/svg">
            <path d="M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14" fill-rule="evenodd"></path>
          </svg>
          </span>Search </button>
        <form class="js-search-form">
          <div class="search__inputWrapper">
          <span class="search__icon">
            <svg height="19px" width="20px" xmlns="http://www.w3.org/2000/svg">
            <path d="M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14" fill-rule="evenodd"></path>
            </svg>
          </span>
          <input class="search__input" name="search" placeholder="Search...">
          </div>
        </form>
        </div>
      </li>
      <li class="navigation-actions__item navigation-hoverable">
        <div class="navigation-language js-select-language">
        <div class="navigation-language__current-language">en <i class="navigation-language__arrow icon-down-dir"></i>
        </div>
        <div class="navigation-dropdown navigation-dropdown_thin navigation-dropdown_origin-right">
          <ul class="navigation-dropdown__sublist">
          <li class="navigation-dropdown__item navigation-dropdown__item_active">
            <a class="navigation-dropdown__link set-app-language" data-language="en" data-track-event="navbar-link-clicked" data-track-link="locale-en" href="" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__language_code_name">
              <div>
              <img class="navigation-dropdown__language_flag" src="https://cdn-firebase.inkitt.com/packs/media/language_flags/en-e013135e.png">
              <span>english</span>
              <span class="navigation-dropdown__language_code">(en)</span>
              </div>
              <div>
              <span class="active_language">
                <svg fill="none" height="10px" viewBox="0 0 14 10" width="14px" xmlns="http://www.w3.org/2000/svg">
                <path d="M12.3333 1L6.40737 8.33333L1.66663 4.31183" stroke="black" stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5"></path>
                </svg>
              </span>
              </div>
            </div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link set-app-language" data-language="es" data-track-event="navbar-link-clicked" data-track-link="locale-es" href="" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__language_code_name">
              <div>
              <img class="navigation-dropdown__language_flag" src="https://cdn-firebase.inkitt.com/packs/media/language_flags/es-937fee20.png">
              <span>español</span>
              <span class="navigation-dropdown__language_code">(es)</span>
              </div>
            </div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link set-app-language" data-language="de" data-track-event="navbar-link-clicked" data-track-link="locale-de" href="" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__language_code_name">
              <div>
              <img class="navigation-dropdown__language_flag" src="https://cdn-firebase.inkitt.com/packs/media/language_flags/de-d99569d2.png">
              <span>deutsch</span>
              <span class="navigation-dropdown__language_code">(de)</span>
              </div>
            </div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link set-app-language" data-language="fr" data-track-event="navbar-link-clicked" data-track-link="locale-fr" href="" target="_self">
            <div class="navigation-dropdown__title navigation-dropdown__language_code_name">
              <div>
              <img class="navigation-dropdown__language_flag" src="https://cdn-firebase.inkitt.com/packs/media/language_flags/fr-461e44b8.png">
              <span>français</span>
              <span class="navigation-dropdown__language_code">(fr)</span>
              </div>
            </div>
            </a>
          </li>
          </ul>
        </div>
        </div>
      </li>
      <li class="navigation-actions__item">
        <button class="navigation-button js-login-signup-anchor navigation-button_dark" data-next-state="signin">sign in</button>
      </li>
      <li class="navigation-actions__item navigation-show_desktop">
        <button class="navigation-button js-login-signup-anchor navigation-button_dark" data-next-state="signup">sign up</button>
      </li>
      <li class="navigation-actions__item navigation-show_desktop navigation-hoverable">
        <div class="navigation-more js-more-links">
        <i class="navigation-more__dots icon-dot-3"></i>
        <div class="navigation-dropdown navigation-dropdown_thin navigation-dropdown_origin-right">
          <ul class="navigation-dropdown__sublist">
          <li class="navigation-dropdown__item">
            <span class="navigation-dropdown__link js-how-it-works-anchor">
            <div class="navigation-dropdown__title">How it works</div>
            </span>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Inkitt Publishing" href="https://www.inkitt.com/writersblog/how-inkitt-publishes-your-books-from-preparation-to-promotion" target="_self">
            <div class="navigation-dropdown__title">Inkitt Publishing</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Inkitt Winners" href="/inkitt-winners" target="_self">
            <div class="navigation-dropdown__title">Inkitt Winners</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Badges" href="/badges" target="_self">
            <div class="navigation-dropdown__title">Badges</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Guidelines" href="/guidelines" target="_self">
            <div class="navigation-dropdown__title">Guidelines</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Support" href="https://inkitt.zendesk.com/hc/en-us" target="_self">
            <div class="navigation-dropdown__title">Support</div>
            </a>
          </li>
          </ul>
          <ul class="navigation-dropdown__sublist">
          <li class="navigation-dropdown__item">
            <a alt="Facebook" class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Facebook" href="https://www.facebook.com/inkitt" target="_blank">
            <div class="navigation-dropdown__title">
              <span class="social-icon icon-facebook-1"></span>Facebook
            </div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a alt="Twitter" class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Twitter" href="https://www.twitter.com/inkitt" target="_blank">
            <div class="navigation-dropdown__title">
              <span class="social-icon icon-twitter"></span>Twitter
            </div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a alt="Blog" class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="Blog" href="/writersblog/" target="_blank">
            <div class="navigation-dropdown__title">
              <span class="social-icon icon-blogger"></span>Blog
            </div>
            </a>
          </li>
          </ul>
          <ul class="navigation-dropdown__sublist">
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="jobs" href="/jobs" target="_self">
            <div class="navigation-dropdown__title">Jobs</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="credits" href="/credits" target="_self">
            <div class="navigation-dropdown__title">Credits</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="terms" href="/terms" target="_self">
            <div class="navigation-dropdown__title">Terms</div>
            </a>
          </li>
          <li class="navigation-dropdown__item">
            <a class="navigation-dropdown__link" data-track-event="navbar-link-clicked" data-track-link="imprint" href="/imprint" target="_self">
            <div class="navigation-dropdown__title">Imprint</div>
            </a>
          </li>
          </ul>
          <div class="navigation-more__note">
          <span class="icon-heart"></span>Inked with love
          </div>
        </div>
        </div>
      </li>
      <li class="navigation-actions__item navigation-hide_desktop">
        <button class="navigation-expander navigation-expander_dark" id="js-navigation-expander">
        <span class="navigation-expander__icon"></span>
        </button>
      </li>
      </ul>
    </div>
    </div>
  </nav>
  """

_part2 = """
  <div class='col-2 story-right-side'></div>
          </div>
          <div class='row'>
          </div>
        </div>
        <div id='story-contest-bar-container' props='{&quot;isAuthorOfCurrentStory&quot;:false}'></div>
      </div>
    </div>
    <div id='inlineCommentsSidebar'></div>
    <div class='non-js-popup-overlay non-js-popup-overlay_dark' id='login-signup-popup' role='dialog' tabindex='-1'>
      <div class='modal login-signup-modal'>
        <a class='popup-cancel js-close-popup' href='#'></a>
        <div class='modal-dialog'>
          <div class='modal-dialog__close'>
            <a class='popup-cancel-icon js-close-popup' href='#'></a>
          </div>
          <div class='modal-content'>
            <div class='login-signup-wrapper js-login-signup-signin'>
              <div class='login-signup-inner'>
                <header class='login-signup__title'>
                  Sign in to Inkitt
                </header>

                <form class='signup-input-fields-wrapper' name='logInForm'>
                  <input class='signin-email' name='username' placeholder='E-mail or Username' type='text'>
                  <input name='password' placeholder='Password' type='password'>
                  <button class='login-signup-btn login-signup-btn_dark' type='submit'>
                    <i class='login-signup-btn__icon icon-spin5 spinner animate-spin feedback-spinner'></i>
                    <span class='login-btn-text'>
                      Sign in
                    </span>
                  </button>
                  <div class='error-wrapper-small js-login-error'></div>
                </form>
                <a class='link-small js-login-signup-switcher' data-next-state='forgot-password'>
                  Forgot your password?
                </a>
                <div class='or-divider'>
                  <span>
                    Or
                  </span>
                </div>
                <div class='login-signup-social'>
                  <div class='google-login-btn' id='google-login-btn'></div>
                  <div class='error-wrapper-small js-login-social-error' id='google-login-error'></div>
                </div>

                <div class='login-signup-subtitle'>
                  You can also
                  <a class='js-login-signup-switcher' data-next-state='signup'>
                    sign up
                  </a>
                </div>
              </div>

            </div>
            <div class='login-signup-wrapper js-login-signup-signup'>
              <div class='login-signup-inner'>
                <header class='login-signup__title'>
                  Sign up with email
                </header>

                <form class='signup-input-fields-wrapper' name='signUpForm'>
                  <input class='signup-email' name='email' placeholder='Enter your E-mail' type='text'>
                  <input class='signup-username' name='username' placeholder='Pick a Username' type='text'>
                  <input name='password' placeholder='Pick a Password' type='password'>
                  <div class='birthday-container'>
                    <label for='birthday_input'>
                      Pick Your Birth Date
                    </label>
                    <div class='birthday-input-wrapper'>
                      <input date-value='Y-m-d' id='birthday_input' name='birthday' type='text' value=''>
                    </div>
                  </div>

                  <div class='error-wrapper-small js-login-error'></div>
                  <button class='login-signup-btn login-signup-btn_dark' type='submit'>
                    <i class='login-signup-btn__icon icon-spin5 spinner animate-spin feedback-spinner'></i>
                    <span class='login-btn-text'>
                      Sign up
                    </span>
                  </button>
                </form>
                <div class='have-an-account-subtitle login-signup-terms'>
                  By signing up on Inkitt, you agree to our
                  <a target="_blank" href="/terms">Terms of Service</a>
                  and
                  <a target="_blank" href="/privacy">Privacy Policy</a>
                </div>
                <div class='have-an-account-subtitle login-signup-subtitle'>
                  Have an account?
                  <a class='js-login-signup-switcher' data-next-state='signin'>
                    Sign in
                  </a>
                </div>
              </div>

            </div>
            <div class='login-signup-wrapper js-login-signup-forgot-password'>
              <div class='login-signup-inner login-signup-forgot-password'>
                <header class='login-signup__title'>
                  Reset Password
                </header>

                <form class='signup-input-fields-wrapper' name='resetPasswordForm'>
                  <input class='resetpassword-email' name='email' placeholder='E-mail address' type='text'>
                  <button class='login-signup-btn login-signup-btn_dark' type='submit'>
                    <i class='icon-spin5 spinner animate-spin feedback-spinner'></i>
                    Reset Password
                  </button>
                  <div class='error-wrapper-small js-login-error'></div>
                  <div class='password-reset-message js-password-reset-message'></div>
                </form>
                <a class='link-small right js-login-signup-switcher' data-next-state='signin'>
                  Cancel
                </a>
              </div>

            </div>
          </div>
        </div>
      </div>
    </div>

    <div id='continue-reading-popup'></div>
    <script>
      window.storyPage = true;
    </script>
    <div class='footerLinksSection'>
      <div class='non-js-popup-overlay' id='how-it-works-popup' role='dialog' tabindex='-1'>
        <div class='modal how-it-works-modal'>
          <span class='popup-cancel js-close-popup'></span>
          <div class='modal-dialog'>
            <div class='modal-dialog__close'>
              <span class='popup-cancel-icon js-close-popup'></span>
            </div>
            <div class='modal-content modal-content_light'>
              <header class='modal-content__header'>
                <h2 class='modal-content__title'>
                  How It Works
                </h2>
                <p class='modal-content__subtitle'>
                  Inkitt’s mission is to discover talented writers and turn them into globally successful authors.
                </p>
              </header>
              <div class='modal-content__body'>
                <ol class='howitworks-steps'>
                  <li class='howitworks-steps__item'>
                    <div class='howitworks-step'>
                      <div class='howitworks-step__counter'>
                        <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/write-e83f00b9.png'
                          srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/write@2x-8cf841fb.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/write@3x-f9a21243.png 3x'>
                      </div>
                      <div class='howitworks-step__title'>
                        Writers Write
                        <span class='howitworks-step__arrow'></span>
                      </div>
                      <p class='howitworks-step__desc'>
                        Authors can write and upload their manuscripts on Inkit for free and writers retain 100% of their
                        copyrights whilst writing on Inkitt
                      </p>
                    </div>
                  </li>
                  <li class='howitworks-steps__item'>
                    <div class='howitworks-step'>
                      <div class='howitworks-step__counter'>
                        <img loading='lazy'
                          src='https://cdn-firebase.inkitt.com/packs/media/frontpage/explore-a0334c35.png'
                          srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/explore@2x-d63d7175.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/explore@3x-675d98dc.png 3x'>
                      </div>
                      <div class='howitworks-step__title'>
                        Readers Discover
                        <span class='howitworks-step__arrow'></span>
                      </div>
                      <p class='howitworks-step__desc'>
                        Readers can read all books for free, without any ads and give the authors feedback.
                      </p>
                    </div>
                  </li>
                  <li class='howitworks-steps__item'>
                    <div class='howitworks-step'>
                      <div class='howitworks-step__counter'>
                        <img loading='lazy'
                          src='https://cdn-firebase.inkitt.com/packs/media/frontpage/publish-9c15ef5f.png'
                          srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/publish@2x-3c30dd6d.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/publish@3x-885a55be.png 3x'>
                      </div>
                      <div class='howitworks-step__title'>
                        We Publish
                        <span class='howitworks-step__arrow'></span>
                      </div>
                      <p class='howitworks-step__desc'>
                        Books that perform well based on their reader engagement are published on our Galatea app.
                      </p>
                    </div>
                  </li>
                </ol>
              </div>
              <div class='modal-content__footer'>
                <ul class='brands-list'>
                  <li class='brands-list__item'>
                    <div class='brands-list-brand'>
                      <img loading='lazy'
                        src='https://cdn-firebase.inkitt.com/packs/media/frontpage/financial-times-363dc69c.png'
                        srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/financial-times@2x-da658ddd.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/financial-times@3x-db8ae23d.png 3x'>
                    </div>
                  </li>
                  <li class='brands-list__item'>
                    <div class='brands-list-brand'>
                      <img loading='lazy'
                        src='https://cdn-firebase.inkitt.com/packs/media/frontpage/theguardian-79eff73f.png'
                        srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/theguardian@2x-529cd7ac.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/theguardian@3x-87c8fd04.png 3x'>
                    </div>
                  </li>
                  <li class='brands-list__item'>
                    <div class='brands-list-brand'>
                      <img loading='lazy'
                        src='https://cdn-firebase.inkitt.com/packs/media/frontpage/bookseller-ca9305c2.png'
                        srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/bookseller@2x-f5a8cdf3.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/bookseller@3x-b285b288.png 3x'>
                    </div>
                  </li>
                  <li class='brands-list__item'>
                    <div class='brands-list-brand'>
                      <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/bbc-c26fe5e1.png'
                        srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/bbc@2x-8666354d.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/bbc@3x-10dbd86a.png 3x'>
                    </div>
                  </li>
                  <li class='brands-list__item'>
                    <div class='brands-list-brand'>
                      <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/gizmodo-a1338237.png'
                        srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/gizmodo@2x-ad14255c.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/gizmodo@3x-60d746d9.png 3x'>
                    </div>
                  </li>
                </ul>
              </div>
            </div>
          </div>
        </div>
      </div>


    </div>

    <div id='fb-root'></div>
    <script type="text/javascript">
      window.fbAsyncInit = function () {
        FB.init({
          appId: '492061657507324',
          status: true,
          cookie: true,
          xfbml: true,
          version: 'v14.0'
        });
      };

      (function (d, s, id) {
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) { return; }
        js = d.createElement(s); js.id = id;
        js.src = "https://connect.facebook.net/en_US/sdk.js";
        fjs.parentNode.insertBefore(js, fjs);
      }(document, 'script', 'facebook-jssdk'));
    </script>


    <!-- Facebook Pixel Code -->
    <script>
      !function (f, b, e, v, n, t, s) {
        if (f.fbq) return; n = f.fbq = function () {
          n.callMethod ?
            n.callMethod.apply(n, arguments) : n.queue.push(arguments)
        };
        if (!f._fbq) f._fbq = n; n.push = n; n.loaded = !0; n.version = '2.0';
        n.queue = []; t = b.createElement(e); t.async = !0;
        t.src = v; s = b.getElementsByTagName(e)[0];
        s.parentNode.insertBefore(t, s)
      }(window, document, 'script',
        'https://connect.facebook.net/en_US/fbevents.js');
      fbq('init', '1629630080621526');
      fbq('track', 'PageView');
    </script>
    <noscript><img height="1" width="1" style="display:none"
        src="https://www.facebook.com/tr?id=1629630080621526&ev=PageView&noscript=1" /></noscript>
    <!-- End Facebook Pixel Code -->

    <script src="https://cdn-firebase.inkitt.com/packs/js/firebase-d0c815ac6205ee187784.js"
      data-ot-ignore="true"></script>
    <script src="https://cdn-firebase.inkitt.com/packs/js/ab_testing-f10d44ba766cf1eb27d2.js"
      data-ot-ignore="true"></script>
    <script src="https://cdn-firebase.inkitt.com/packs/js/base_story-885f028d6ac382264839.js"
      data-ot-ignore="true"></script>
    <script src="https://cdn-firebase.inkitt.com/packs/js/story_page-f484cf559f82b1780cd4.js"
      data-ot-ignore="true"></script>


    <noscript>
      <iframe height='0' src='https://www.googletagmanager.com/ns.html?id=GTM-NHH9V9G'
        style='display:none;visibility:hidden' width='0'></iframe>
    </noscript>
    <script type='application/ld+json'>
  {
  "@context" : "http://schema.org",
  "@type" : "Organization",
  "name" : "Inkitt",
  "url" : "https://www.inkitt.com",
  "sameAs" : [
  "https://www.facebook.com/inkitt",
  "https://www.twitter.com/inkitt"
  ],
  "logo": "http://www.inkitt.com/1024_onblack-min.png"
  }
  </script>

    <section class='extendedFooter' navbar='true'>
      <div class='extendedFooter_wrap'>
        <div class='extendedFooter_column extendedFooter_column-about'>
          <div class='extendedFooter_title'>
            About Us
          </div>
          <p class='extendedFooter_description'>
            Inkitt is the world’s first reader-powered publisher, providing a platform to discover hidden talents and turn
            them into globally successful authors. Write captivating stories, read enchanting novels, and we’ll publish
            the books our readers love most on our sister app, GALATEA and other formats.
          </p>
        </div>
        <div class='extendedFooter_column extendedFooter_column-authors'>
          <div class='extendedFooter_title'>
            Inkitt for Authors
          </div>
          <ul class='extendedFooter_links'>
            <li class='extendedFooter_link'>
              <a target="_self" href="/writing-contests-list">Writing Contests List</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self"
                href="https://www.inkitt.com/writersblog/how-inkitt-publishes-your-books-from-preparation-to-promotion">Inkitt
                Publishing</a>
            </li>
            <li class='extendedFooter_link'>
              <a class="js-create-story" href="#">Submit Your Story</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/guidelines">Guidelines</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/groups">Writing Groups</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/author-subscriptions-terms">Author Subscriptions</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self"
                href="https://inkitt.zendesk.com/hc/en-us/articles/360015784599-What-is-a-DMCA-notice-and-how-to-use-it-">Report
                Plagiarism</a>
            </li>
          </ul>
        </div>
        <div class='extendedFooter_column extendedFooter_column-readers'>
          <div class='extendedFooter_title'>
            Inkitt for Readers
          </div>
          <ul class='extendedFooter_links'>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/fantasy">Fantasy Books</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/scifi">Sci-Fi Books</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/romance">Romance Books</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/drama">Drama Books</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/thriller">Thriller Books</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/mystery">Mystery Books</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/genres/horror">Horror Books</a>
            </li>
          </ul>
        </div>
        <div class='extendedFooter_column extendedFooter_column-community'>
          <div class='extendedFooter_title'>
            Inkitt Community
          </div>
          <ul class='extendedFooter_links'>
            <li class='extendedFooter_link'>
              <a target="_self" href="/writersblog">The Writer&#39;s Blog</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_blank" rel="noopener" href="https://twitter.com/Inkitt">Twitter</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_blank" rel="noopener" href="https://www.facebook.com/inkitt/">Facebook</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_blank" rel="noopener" href="https://www.instagram.com/inkittbooks/">Instagram</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_blank" rel="noopener" href="https://inkitt.zendesk.com/hc/en-us">Support</a>
            </li>
            <li class='extendedFooter_link'>
              <a target="_self" href="/jobs">Join the Inkitt Team</a>
            </li>
          </ul>
        </div>
        <div class='extendedFooter_column extendedFooter_column-apps'>
          <div class='wrap'>
            <a alt='Download The Inkitt iOS App' class='appBanner'
              href='https://itunes.apple.com/us/app/inkitt-free-books-fiction/id1033598731?footer_ext'
              onclick='mixpanelHelper(&#39;user-clicked-download-from-app-store&#39;, { user_id: globalData.currentUser?.id || null, visitor_id: ahoy.getVisitorId(), page_name: document.title, page_url: window.location.href})'
              rel='noopener' target='_blank'>
              <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/images/ios_banner-ef5031be.svg'>
            </a>
            <a alt='Get Inkitt App on Google Play' class='appBanner appBanner-android'
              href='https://play.google.com/store/apps/details?id=com.inkitt.android.hermione&amp;hl=en&amp;utm_source=website_footer&amp;pcampaignid=MKT-Other-global-all-co-prtnr-py-PartBadge-Mar2515-1'
              onclick='mixpanelHelper(&#39;user-clicked-download-from-google-play&#39;, { user_id: globalData.currentUser?.id || null, visitor_id: ahoy.getVisitorId(), page_name: document.title, page_url: window.location.href})'
              rel='noopener' target='_blank'>
              <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/images/android_banner-6dd04511.svg'>
            </a>
          </div>
        </div>
      </div>
      <div class='extendedFooterTrack_wrap'>
        <ul class='extendedFooterTrack_links'>
          <li class='extendedFooterTrack_link'>
            <a target="_self" href="/imprint">Imprint</a>
          </li>
          <li class='extendedFooterTrack_link'>
            <a target="_self" href="/privacy">Privacy Policy</a>
          </li>
          <li class='extendedFooterTrack_link'>
            <a target="_self" href="/terms">Terms</a>
          </li>
        </ul>
      </div>
    </section>

    <script>
      // jQuery(function() {
      //   jQuery.scrollDepth();
      // });
    </script>
  </body>

  </html> """

inkittcom_story_html_return =("""
  <!DOCTYPE html>
  <html>
  <head>
  <title>Finding Me by kyliet at Inkitt</title>
  <link href='https://static-firebase.inkitt.com/manifest.json' rel='manifest'>
  <!-- Open Graph data -->
  <meta content='492061657507324' property='fb:app_id'>
  <link href='https://www.inkitt.com/stories/drama/1176584' rel='canonical'>
  <meta content='index, follow' name='robots'>
  <meta content='Finding Me - Free Novel by kyliet' property='og:title'>
  <meta content='kyliet' property='author'>
  <meta content='kyliet' name='author'>
  <meta content='article' property='og:type'>
  <meta content='1280' property='og:image:width'>
  <meta content='450' property='og:image:height'>
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' property='og:image'>
  <meta
    content='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...'
    property='og:description'>
  <meta content='Inkitt' property='og:site_name'>
  <meta content='2024-09-19 06:27:49 UTC' property='og:updated_time'>
  <meta content='http://www.inkitt.com/stories/1176584' property='og:url'>
  <meta
    content='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...'
    name='description'>
  <!-- Schema.org markup for Google+ -->
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' itemprop='image'>
  <!-- Twitter Card data -->
  <meta content='summary_large_image' name='twitter:card'>
  <meta content='@inkitt' name='twitter:site'>
  <meta content='Finding Me - Free Novel by kyliet' name='twitter:title'>
  <meta
    content='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...'
    name='twitter:description'>
  <!-- Twitter summary card with large image must be at least 280x150px -->
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' name='twitter:image:src'>
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' name='twitter:image'>
  <!-- Pinterest -->
  <!-- / %meta{:content => @story.author.name, :property => "article:author"} -->
  <meta content='2024-01-29 02:20:09 UTC' property='article:published_time'>
  <script type="application/ld+json">{"@context":"http://schema.org","@type":"Article","mainEntityOfPage":{"@type":"WebPage","@id":"https://www.inkitt.com/stories/fanfiction/1176584"},"headline":"Finding me","image":{"@type":"ImageObject","url":"https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg","height":450,"width":1280},"datePublished":"2024-01-29T02:20:09.595Z","dateModified":"2024-09-19T06:27:49.102Z","author":{"@type":"Person","name":"kyliet"},"description":"Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...","publisher":{"@type":"Organization","name":"Inkitt GmbH","logo":{"@type":"ImageObject","url":"https://cdn-firebase.inkitt.com/images/inkitt_door_sign_small.jpg"}}}
  </script>
    <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/base-ac4318c9.css" />
    <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/story_page-60fc35e6.css" />
    <link rel="stylesheet" media="print" href="https://cdn-firebase.inkitt.com/packs/css/block_print-9c951945.css" />
    <link rel="prefetch" media="all"
      href="https://fonts.googleapis.com/css?family=Droid+Serif:400,700,400italic,700italic|Raleway:300,400,500,700&amp;display=swap"
      as="style" />

    <link href='https://cdn-firebase.inkitt.com/packs/media/images/fav_inkitt-4186e304.jpg' rel='icon' type='image/jpeg'>
    <script>
      globalData.storyId = 1176584;
      globalData.inlineCommentsAllowed = true;
      globalData.isAuthorOfCurrentStory = false;
      globalData.chapter = { "id": 5405826, "chapter_number": 1, "name": "Authors note", "comments_count": 1 };
      globalData.previewMode = false;
      globalData.authorPatronTiers = [];
      globalData.currentV2Patronage = null;
      globalData.featuredPatronTierSettings = null
      globalData.author = { "id": 3028573, "username": "kyliet", "name": "kyliet", "description": null, "small_profile_picture_url": "https://cdn-gcs.inkitt.com/profilepictures/small_17b78a1c8e8d5aadf4911fce06fe077f.jpg" };
      globalData.isMobileOrTablet = false;
      globalData.shouldShowPatronOnly = true;
      globalData.authorUsername = "kyliet";
      globalData.authorName = "kyliet";
      globalData.isAuthorFollowed = false;
      globalData.isReadingPositionTrackable = true;
    </script>
  </head>
  """
+ _part1 + 
  """ <div id="reading-chapter-progress-container" props="{&quot;read_progress&quot;:[{&quot;percentage&quot;:0.9998863765481195,&quot;status&quot;:&quot;current&quot;},{&quot;percentage&quot;:3.2212248608112715,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.2098625156232248,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.2496307237813884,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.033746165208499,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1814566526531074,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.962617884331326,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.090557891148733,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1558913759800022,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.207021929326213,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1985001704351776,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.417225315305079,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.763776843540507,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.2013407567321894,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.073400749914782,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.596182252016816,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5081240768094535,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5819793205317576,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5564140438586525,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.010907851380525,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1530507896829905,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.8518350187478694,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.596182252016816,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.7098057038972843,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.50244290421543,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.050676059538689,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5336893534825586,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.848994432450858,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.5335757300306785,&quot;status&quot;:&quot;notread&quot;}]}"></div>
  <div class="page StoryPage">
 <div class="story-page story-id-1176584" id="page-internal">
  <div class="story-horizontal-cover" data-cover-url="https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg" data-is-test="false" data-summary="Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before she was born so the name stuck.

  Parker takes care of her family. She cooks and cleans for her brothers when her parents are off travelling the world. At 18 she has never so much as kissed a boy let alone had a boyfriend. She doesn&#39;t have time for it between studying, working and looking after her brothers. She didn&#39;t mind, that&#39;s what families did apparently.

  As her graduation draws near her parents and brothers promise to be there. She is excited to finally be finishing high school. She had been accepted to university on the other side of the country but was reluctant to accept because it would mean leaving behind her family.

  Parker&#39;s brothers are working in the family business since there dad retired to travel with there mother. Leon is 26, Jude is 23 and Tanner is 22. They are play boys and are loving life. They have no responsibilitIes at home because Parker takes care of them. They forget all about her graduation until the day after it occurs as do her parents. They vow to make it up to her but when she doesn&#39;t come home they know they have made the biggest mistake of there lives.

  Parker is hurt by her family. Her brothers friend, who had seen everything that had been ha" data-test-type="titles" data-title="Finding me">
   <div class="story-horizontal-cover__back story-horizontal-cover__back_blurred" itemprop="image" style="background-image:url(&#39;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg&#39;)"></div>
   <div class="story-horizontal-cover__front-wrap">
    <div id="image-zoom" props="{&quot;cover&quot;:{&quot;url&quot;:&quot;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg&quot;},&quot;storyTitle&quot;:&quot;Finding me&quot;,&quot;className&quot;:&quot;story-horizontal-cover__front&quot;}"></div>
   </div>
  </div>
  <div class="container">
   <div class="row no-gutters">
    <div class="col-2 story-left-side offset-1">
     <div class="showed-block">
      <div class="sticky-left-pan" style="display:none"></div>
      <div id="like-story-button"></div>
      <button class="button show-reading-lists-button" id="show-reading-lists-button">
       <i class="icon-white icon-bookmark"></i>
       <span class="big-screen">Add to Reading List</span>
       <span class="small-screen">Reading List</span>
      </button>
      <div id="reading-lists-block-container" props="{&quot;storyId&quot;:1176584}"></div>
      <div style="position:relative">
       <div class="write-review-tooltip" style="display:none">
        <div class="arrow_box"></div>kyliet would love your feedback! Got a few minutes to write a review? <i class="icon-cancel-1"></i>
       </div>
       <a class="button create-review-button" href="/stories/drama/1176584/reviews/new">Write a Review</a>
      </div>
      <div id="sharing-widget-container" props="{&quot;facebookIcon&quot;:true,&quot;includeTumblr&quot;:true,&quot;name&quot;:&quot;Read Finding me for free on Inkitt.&quot;,&quot;shareLocation&quot;:&quot;storypage&quot;,&quot;shareUrl&quot;:&quot;https://www.inkitt.com/stories/drama/1176584&quot;,&quot;storyId&quot;:1176584,&quot;disabled&quot;:false}"></div>
      <div id="report-story-button"></div>
      <div id="custom-styling-container"></div>
     </div>
    </div>
    <div class="col-6 story-middle-column">
     <header class="story-header" data-profile-tracking-source="Story">
      <h1 class="story-title story-title--big">Finding me</h1>
      <div class="author-block">
       <a class="author-link" data-cta="Profile Picture" href="/kyliet" track-profile-click="true">
        <img class="profile-picture" src="https://cdn-gcs.inkitt.com/profilepictures/small_17b78a1c8e8d5aadf4911fce06fe077f.jpg">
       </a>
       <div class="block-1">
        <a class="author-link" data-cta="Username" href="/kyliet" track-profile-click="true">
         <span class="name" id="storyAuthor">kyliet</span>
        </a>
        <a class="stories-count author-link" data-cta="Story Count" href="/kyliet" track-profile-click="true">17 stories</a>
       </div>
       <div class="block-2" id="follow-button-container" props="{&quot;user&quot;:{&quot;id&quot;:3028573,&quot;is_followed&quot;:false}}"></div>
      </div>
      <p class="all-rights-reserved">All Rights Reserved ©</p>
      <div class="content-labels-frame">
       <p class="content-labels">This story contains themes of: assault, child abuse, domestic violence, drug use overdose, ableism, racism, suicide</p>
      </div>
      <h2 class="story-author-notes__title">Story Notes</h2>
      <div class="story-author-notes__text">This story is unedited and contains racism</div>
      <h2>Summary</h2>
      <p class="story-summary">Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before she was born so the name stuck. Parker takes care of her family. She cooks and cleans for her brothers when her parents are off travelling the world. At 18 she has never so much as kissed a boy let alone had a boyfriend. She doesn&#39;t have time for it between studying, working and looking after her brothers. She didn&#39;t mind, that&#39;s what families did apparently. As her graduation draws near her parents and brothers promise to be there. She is excited to finally be finishing high school. She had been accepted to university on the other side of the country but was reluctant to accept because it would mean leaving behind her family. Parker&#39;s brothers are working in the family business since there dad retired to travel with there mother. Leon is 26, Jude is 23 and Tanner is 22. They are play boys and are loving life. They have no responsibilitIes at home because Parker takes care of them. They forget all about her graduation until the day after it occurs as do her parents. They vow to make it up to her but when she doesn&#39;t come home they know they have made the biggest mistake of there lives. Parker is hurt by her family. Her brothers friend, who had seen everything that had been ha</p>
      <div class="dls">
       <div class="dlc">
        <dl>
         <dt>Genre:</dt>
         <dd class="genres">
          <a href="/genres/drama">Drama</a>
         </dd>
        </dl>
        <dl>
         <dt>Author:</dt>
         <dd>
          <a class="author-link" data-cta="Username in Story Info" track-profile-click="true" href="/kyliet">kyliet</a>
         </dd>
        </dl>
       </div>
       <div class="dlc">
        <dl>
         <dt>Status:</dt>
         <dd>Complete</dd>
        </dl>
        <dl>
         <dt>Chapters:</dt>
         <dd>29</dd>
        </dl>
       </div>
       <div class="dlc">
        <dl>
         <dt>Rating:</dt>
         <dd class="rating">
          <span class="star">★</span>4.8 <a class="show-all-reviews-link" href="/stories/drama/1176584/reviews">82 reviews</a>
         </dd>
        </dl>
        <dl>
         <dt>Age Rating:</dt>
         <dd>18+</dd>
        </dl>
       </div>
      </div>
     </header>
     <article class="default-style" id="story-text-container" style="font-size:22px">
      <h2 class="chapter-head-title">Authors note</h2>
      <div class="" style="position:relative">
       <div class="story-page-text" id="chapterText">
        <p data-content="2272306445">This story deals with things that may trigger certain people. I do not put trigger warnings on each chapter so be warned.</p>
        <p data-content="209879444">
         <br>
        </p>
        <p data-content="2349762256">I am not a professional author at all. I write for fun and as a way to cope with PTSD. There will be errors in spelling and grammar and I apologise for that now. I do try to edit my stories but being dyslexic I sometimes don't see an error. If you see one please point it out and I'll correct it.</p>
        <p data-content="209879444">
         <br>
        </p>
        <p data-content="3031259999">Second I am an Australian which means some spelling and sayings I use in my work will be different to what you are use to. I also sometimes use Australian slang. If you don't understand something just ask me and I'll explain. My writing style is different to what some people are use to because it seems that Australian's were taught a little differently. My work is based on Australian schooling and university so again it may be different to what you are use to reading. I write what I know so yeah.</p>
        <p data-content="209879444">
         <br>
        </p>
        <p data-content="1942423886">I own all the rights to all my stories and I do not give permission for anyone to use my work or copy it at all. I only ever publish my stories on Wattpad so if you see my work elsewhere and that someone has copied it please report to me and also to wherever you see the work. I try to make my stories unpredictable and not follow the same story lines. I work hard to keep people interested and don't appreciate people thinking they can just copy what I have done to make their own stories.</p>
        <p data-content="209879444">
         <br>
        </p>
        <p data-content="3438669947">I love getting feedback on my work with the comments and votes. It helps motivate me to keep writing. I know not everyone likes my work and that's ok but please don't be rude or nasty about it. If you don't like it don't read it.</p>
        <p data-content="209879444">
         <br>
        </p>
        <p data-content="3578649133">Thank you for clicking on the short story and I hope you like it.</p>
        <p data-content="209879444">
         <br>
        </p>
        <p data-content="872150574">Take care and keep safe.</p>
        <p data-content="1102070107">Smiley xx</p>
       </div>
      </div>
     </article>
    </div>
    <div class="col-3 story-right-side">
     <div class="showed-block">
      <div class="sticky-right-pan">
       <div class="chapters-list" style="display:none">
        <div class="current-chapter">
         <i class="icon-angle-down"></i>
         <strong>Chapters</strong>
         <div class="chapter-name">1. Authors note</div>
        </div>
        <ul class="nav nav-list chapter-list-dropdown">
         <li class="active">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/1">
           <span class="chapter-nr">1</span>
           <span class="chapter-title">Authors note</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/2">
           <span class="chapter-nr">2</span>
           <span class="chapter-title">Prolgue</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/3">
           <span class="chapter-nr">3</span>
           <span class="chapter-title">Chapter 1</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/4">
           <span class="chapter-nr">4</span>
           <span class="chapter-title">Chapter 2</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/5">
           <span class="chapter-nr">5</span>
           <span class="chapter-title">Chapter 3</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/6">
           <span class="chapter-nr">6</span>
           <span class="chapter-title">Chapter 4</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/7">
           <span class="chapter-nr">7</span>
           <span class="chapter-title">Chapter 5</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/8">
           <span class="chapter-nr">8</span>
           <span class="chapter-title">Chapter 6</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/9">
           <span class="chapter-nr">9</span>
           <span class="chapter-title">Chapter 7</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/10">
           <span class="chapter-nr">10</span>
           <span class="chapter-title">Chapter 8</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/11">
           <span class="chapter-nr">11</span>
           <span class="chapter-title">Chapter 9</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/12">
           <span class="chapter-nr">12</span>
           <span class="chapter-title">Chapter 10</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/13">
           <span class="chapter-nr">13</span>
           <span class="chapter-title">Chapter 11</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/14">
           <span class="chapter-nr">14</span>
           <span class="chapter-title">Chapter 12</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/15">
           <span class="chapter-nr">15</span>
           <span class="chapter-title">Chapter 13</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/16">
           <span class="chapter-nr">16</span>
           <span class="chapter-title">Chapter 14</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/17">
           <span class="chapter-nr">17</span>
           <span class="chapter-title">Chapter 15</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/18">
           <span class="chapter-nr">18</span>
           <span class="chapter-title">Chapter 16</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/19">
           <span class="chapter-nr">19</span>
           <span class="chapter-title">Chapter 17</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/20">
           <span class="chapter-nr">20</span>
           <span class="chapter-title">Chapter 18</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/21">
           <span class="chapter-nr">21</span>
           <span class="chapter-title">Chapter 19</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/22">
           <span class="chapter-nr">22</span>
           <span class="chapter-title">Chapter 20</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/23">
           <span class="chapter-nr">23</span>
           <span class="chapter-title">Chapter 21</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/24">
           <span class="chapter-nr">24</span>
           <span class="chapter-title">Chapter 22</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/25">
           <span class="chapter-nr">25</span>
           <span class="chapter-title">Chapter 23</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/26">
           <span class="chapter-nr">26</span>
           <span class="chapter-title">Chapter 24</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/27">
           <span class="chapter-nr">27</span>
           <span class="chapter-title">Chapter 25</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/28">
           <span class="chapter-nr">28</span>
           <span class="chapter-title">Chapter 26</span>
          </a>
         </li>
         <li class="">
          <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/29">
           <span class="chapter-nr">29</span>
           <span class="chapter-title">Epilogue</span>
          </a>
         </li>
        </ul>
       </div>
      </div>
     </div>
    </div>
   </div>
   <div class="row no-gutters">
    <div class="col-2 story-left-side"></div>
    <div class="col-8 story-middle-column">
     <a class="inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn" href="" id="continue-reading-btn">Continue Reading</a>
    </div>
    <div class="col-2 story-right-side"></div>
   </div>
   <div class="row no-gutters">
    <div class="col-2 story-left-side"></div>
    <div class="col-8 story-middle-column">
     <article class="default-style" id="story-text-container" style="font-size:22px"></article>
     <div id="follow-modal-position"></div>
     <a class="inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn" target="_self" id="next-chapter-btn" href="/stories/drama/1176584/chapters/2">Next Chapter</a>
     <div id="story-post-chapter-reviews"></div>
     <div id="story-comments"></div>
     <div id="author-follow-modal"></div>
    </div>
  """
+ _part2)

inkittcom_html_chapter_return = """
  <!DOCTYPE html>
  <html>
  <head>
  <script>
    window.__webpack_public_path__ = "https://cdn-firebase.inkitt.com/packs/"
  </script>

  <!-- = OneTrust Cookies Consent Notice start for inkitt.com -->
  <script async src='https://cdn.cookielaw.org/consent/5137c3da-f268-424d-8e51-758eb87b957a/OtAutoBlock.js' type='text/javascript'></script>
  <script async charset='UTF-8' data-domain-script='5137c3da-f268-424d-8e51-758eb87b957a' data-language='en_US' src='https://cdn.cookielaw.org/scripttemplates/otSDKStub.js' type='text/javascript'></script>
  <script>
    function OptanonWrapper() {}
  </script>

  <title>Chapter Chapter 1 | Finding Me by kyliet at Inkitt</title>
  <link href='https://static-firebase.inkitt.com/manifest.json' rel='manifest'>
  <!-- Open Graph data -->
  <meta content='492061657507324' property='fb:app_id'>
  <link href='https://www.inkitt.com/stories/drama/1176584' rel='canonical'>
  <meta content='index, follow' name='robots'>
  <meta content='Finding Me - Free Novel by kyliet' property='og:title'>
  <meta content='kyliet' property='author'>
  <meta content='kyliet' name='author'>
  <meta content='article' property='og:type'>
  <meta content='1280' property='og:image:width'>
  <meta content='450' property='og:image:height'>
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' property='og:image'>
  <meta content='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...' property='og:description'>
  <meta content='Inkitt' property='og:site_name'>
  <meta content='2024-09-19 06:27:49 UTC' property='og:updated_time'>
  <meta content='http://www.inkitt.com/stories/1176584' property='og:url'>
  <meta content='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...' name='description'>
  <!-- Schema.org markup for Google+ -->
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' itemprop='image'>
  <!-- Twitter Card data -->
  <meta content='summary_large_image' name='twitter:card'>
  <meta content='@inkitt' name='twitter:site'>
  <meta content='Finding Me - Free Novel by kyliet' name='twitter:title'>
  <meta content='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...' name='twitter:description'>
  <!-- Twitter summary card with large image must be at least 280x150px -->
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' name='twitter:image:src'>
  <meta content='https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg' name='twitter:image'>
  <!-- Pinterest -->
  <!-- / %meta{:content => @story.author.name, :property => "article:author"} -->
  <meta content='2024-01-29 02:20:09 UTC' property='article:published_time'>
  <script type="application/ld+json">{"@context":"http://schema.org","@type":"Article","mainEntityOfPage":{"@type":"WebPage","@id":"https://www.inkitt.com/stories/drama/1176584"},"headline":"Finding me","image":{"@type":"ImageObject","url":"https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg","height":450,"width":1280},"datePublished":"2024-01-29T02:20:09.595Z","dateModified":"2024-09-19T06:27:49.102Z","author":{"@type":"Person","name":"kyliet"},"description":"Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before...","publisher":{"@type":"Organization","name":"Inkitt GmbH","logo":{"@type":"ImageObject","url":"https://cdn-firebase.inkitt.com/images/inkitt_door_sign_small.jpg"}}}
  </script>
  <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/base-ac4318c9.css" />
  <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/story_page-60fc35e6.css" />
  <link rel="stylesheet" media="print" href="https://cdn-firebase.inkitt.com/packs/css/block_print-9c951945.css" />
  <link rel="prefetch" media="all" href="https://fonts.googleapis.com/css?family=Droid+Serif:400,700,400italic,700italic|Raleway:300,400,500,700&amp;display=swap" as="style" />

  <script>
    var globalData = {
      page: {
        controller: "stories",
        action: "prerendered_show"
      },
      currentUser: null,
      config: {
        facebookScope: "public_profile,email",
        env: "production",
        firebase: {"apiKey":"AIzaSyAuIEemKjahqN3uMSD5mdAJQ5rT_t3aFSU","authDomain":"inkitt-3ce9d.firebaseapp.com","databaseURL":"https://inkitt-3ce9d.firebaseio.com","projectId":"inkitt-3ce9d","storageBucket":"inkitt-3ce9d.appspot.com","messagingSenderId":"2681802959","appId":"1:2681802959:web:85dbda88523a8d2d","measurementId":"G-RPW9BSNPP4","vapidKey":"BNxdPSC7cXueHnt7Gy4HY_rc8tzQJ8DFjvA2cI5FL6tYviIoOdrIA2Ctx3M5H7mbY-CkUx5rJzYvTFUgniqM2CQ"},
        ahoyAuthorizationHeaderName: "Authorization",
        stripePublishableKey: "pk_live_51N0qiOAyHjL0HQQs0jooC09Ox9Jcy6pMrjgmKgsoSBZI0QUkWXRWPLNlhll0iCQwdlc585Ctx8hGWhvsqMRlrN3F00BFrRA6i0"
      },
      language: 'en',
      globalSettings: {"id":1,"galatea_promo_codes_status":"active"},
      isMobileOrTablet: false
    };
  </script>
  <script>
    globalData.user = {};
  </script>

  <link href='https://cdn-firebase.inkitt.com/packs/media/images/fav_inkitt-4186e304.jpg' rel='icon' type='image/jpeg'>
  <script>
    globalData.storyId = 1176584;
    globalData.inlineCommentsAllowed = true;
    globalData.isAuthorOfCurrentStory = false;
    globalData.chapter = {"id":5405856,"chapter_number":3,"name":"Chapter 1","comments_count":2};
    globalData.previewMode = false;
    globalData.authorPatronTiers = [];
    globalData.currentV2Patronage = null;
    globalData.featuredPatronTierSettings = null
    globalData.author = {"id":3028573,"username":"kyliet","name":"kyliet","description":null,"small_profile_picture_url":"https://cdn-gcs.inkitt.com/profilepictures/small_17b78a1c8e8d5aadf4911fce06fe077f.jpg"};
    globalData.isMobileOrTablet = false;
    globalData.shouldShowPatronOnly = true;
    globalData.authorUsername = "kyliet";
    globalData.authorName = "kyliet";
    globalData.isAuthorFollowed = false;
    globalData.isReadingPositionTrackable = true;
  </script>
  <script class='optanon-category-C0002' type='text/plain'>
  <!-- / Google Tag Manager code begins -->
  (function(w,d,s,l,i){w[l]=w[l]||[];w[l].push({'gtm.start':
  new Date().getTime(),event:'gtm.js'});var f=d.getElementsByTagName(s)[0],
  j=d.createElement(s),dl=l!='dataLayer'?'&l='+l:'';j.async=true;j.src=
  'https://www.googletagmanager.com/gtm.js?id='+i+dl;f.parentNode.insertBefore(j,f);
  })(window,document,'script','dataLayer','GTM-NHH9V9G');
  <!-- / Google Tag Manager code ends -->
  </script>

  <meta content='width=device-width, initial-scale=1.0' name='viewport'>
  <script>
  //<![CDATA[
  window.__CSS_CHUNKS__ = {}
  //]]>
  </script>
  </head>
  <body class='StoryPage' id='StoryPage'>
  <nav class='navigation navigation_white'>
  <div class='navigation__left'>
  <a class='navigation__brand navigation__brand_dark' href='/' target='_self' title='Inkitt - Free Books, Stories and Novels'>
  <svg viewBox='0 0 423.5 134.29' xmlns='http://www.w3.org/2000/svg'>
  <g>
  <path d='M68.37,16.5c1-2.43,3.1-8.6-3.6-16.4-5.9,8.35-14.48,8.22-23.15,8.09l-21.9,0C11.39,8.18,4.57,11.11,1,19.31c-3.65,8.43,3.59,16.39,3.59,16.39,5.9-8.35,14.49-8.22,23.15-8.08.64,0,5.07,0,14.33,0,0,0-4,0,7.58-.07C58,27.56,65,24.78,68.37,16.5Z'></path>
  <path d='M77.43,118.66c2.16-2.23,4.91-19.57-.42-20.09-2.18,13.23-15.46,16.28-18.21,16.34-3.11.07-15.47.05-17.18,0-9-.14-10.13-.26-21.9-.23-8.33,0-15.14,2.88-18.69,11.08a12.91,12.91,0,0,0-.6,8.32l41.67,0S61.31,135.31,77.43,118.66Z'></path>
  <path d='M93.32,45.28c-10.11-1.89-17.18,3.29-24,10.21C75.69,60.18,77,66.41,77,73.3c0,1.1,0,31.16,0,32.21,0,3.08-.51,13.55-.51,13.55,7.41,18.27,22.8,19.68,34.29,6a24.56,24.56,0,0,1-6.22-14.94c-.13-2.67-.15-4.81-.15-5.06,0-3.95,0-26.52,0-26.78a8.7,8.7,0,0,1,.51-2.56c2.32-4.78,11-9,11-9a13.92,13.92,0,0,1,8.63-1.86c4.49.62,6.11,3.31,6.16,7.39h0c0,13,0,21,0,34,0,1.82,0,3.64,0,5.46.22,18.16,9.58,26,26.9,21.18,7.94-2.19,15.13-6.74,22.82-10.19,8.16,15,24.15,15.64,34.11.52-7.95-7.45-7.62-12-7.85-30.55,5.84-.79,12,1.09,15,6a60.46,60.46,0,0,1,6.84,16.11c4.28,16.44,14.45,22.86,30.09,17.87,7.2-2.29,20.9-9.37,21.07-9.46,2.91,9,10.32,11.61,19.37,11,10.68-.71,28.81-12.82,32.44-15.87l0-25c0,10.67-5.58,18-16,20.87-5.72,1.57-9.23-.83-9.87-6.85-.17-1.57,0-48.32,0-50.64,0-12.79-9.45-18.23-20.3-15.63-6.25,1.5-11.62,4.65-15.18,10.65,6.53,2.7,8.1,9.1,8.1,15.16,0,12.29,0,22.12,0,34.41a13.54,13.54,0,0,1-14.59,13.63c-5-.5-5.4-4.51-5.59-7-1.51-18.83-8.85-23.27-22.76-24.22-.32,0,8.54-6.13,13.91-15.54,5-8.8,3.13-21.57-3.26-27.17-5.45-4.78-15.17-4.3-24.15,1.67-4.82,3.21-9.21,7.07-14.9,11.48,0,0,.11-16.14,0-25.11-.14-8.67-.26-17.25,8.08-23.15-7.8-6.69-15.65-7.24-24.09-3.6-8.2,3.55-11.14,10.36-11.16,18.69-.07,27.77.05,52.66,0,80.43,0,6.43-7.41,13.11-14.46,13.19-5.51.07-7.23-2.74-7.25-12,0-15.25.25-25-.13-40.23h-.06c0-6.26-2.2-12.39-6.13-15.83-5.45-4.78-15.17-4.3-24.14,1.68-4.82,3.21-9.21,7.07-14.9,11.48l-8.25,6.46C104.59,50.83,100,46.53,93.32,45.28ZM206.93,61.89c.09-3.6,6.57-6.85,11.86-6.12,4.83.66,6.28,3.86,5.89,8.31-.66,7.65-7.75,17-17.81,22.4C206.87,77.68,206.74,69.79,206.93,61.89Z'></path>
  <circle cx='292.47' cy='14.42' r='14.42'></circle>
  <path d='M346.27,2.38C337.84-1.27,330-.72,322.19,6c8.35,5.9,8.22,14.49,8.08,23.15-.07,4.38-.14,85.05-.14,87.58a27.79,27.79,0,0,0,1.45,6.82c2.92,9,10.32,11.19,19.38,10.58,10.67-.71,19.53-5.54,27.73-12,1.47-1.15,3-2.23,4.71-3.49l0-25c0,10.67-5.58,18-16,20.87-5.72,1.57-9.23-.82-9.87-6.85-.17-1.57-.12-86.61-.12-86.61C357.33,12.74,354.48,5.93,346.27,2.38Z'></path>
  <path d='M405.85,21.07c0-8.33-2.88-15.14-11.08-18.69C386.33-1.27,378.47-.72,370.68,6c8.35,5.9,8.22,14.49,8.09,23.15-.07,4.38-.14,85.05-.14,87.58a27.79,27.79,0,0,0,1.45,6.82c2.91,9,10.32,11.19,19.38,10.58A42.81,42.81,0,0,0,416.8,129c6.62-3.53,7.71-12.59,5.94-17.45a25.38,25.38,0,0,1-6.91,3c-5.72,1.57-9.36-.82-10-6.85C405.66,106.11,405.88,34.09,405.85,21.07Z'></path>
  <path d='M51.38,18c0-8.33-26.95-.61-27.08,8.06-.07,4.37-.14,88.09-.14,90.62a27.74,27.74,0,0,0,1.46,6.82c2.91,9,10.32,11.19,19.37,10.58,10.67-.71,19.53-5.54,27.73-12,1.47-1.15,3-2.23,4.71-3.49l0-25c0,10.67-5.58,18-16,20.87-5.72,1.57-9.22-.82-9.87-6.85C51.33,106.11,51.42,31.06,51.38,18Z'></path>
  <path d='M422.35,48.67c1-2.43,3.1-8.6-3.59-16.4-5.9,8.35-14.48,8.22-23.16,8.09l-63.05,0c-8.33,0-15.14,2.95-18.69,11.15-3.65,8.43,3.59,16.4,3.59,16.4,5.9-8.35,14.49-8.22,23.15-8.09l55.47,0s-4,0,7.58-.07C412,59.73,419,56.95,422.35,48.67Z'></path>
  </g>
  </svg>

  </a>
  <div class='navigation-group navigation-group_mobile js-navigation-mobile-menu'>
  <div class='search js-search search_fullwidth'>
  <button class='search__expander navigation-hoverable' data-track-source='Search Bar'>
  <span class='search__icon'>
  <svg height='19px' width='20px' xmlns='http://www.w3.org/2000/svg'>
  <path d='M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14' fill-rule='evenodd'></path>
  </svg>
  </span>
  Search
  </button>
  <form class='js-search-form'>
  <div class='search__inputWrapper'>
  <span class='search__icon'>
  <svg height='19px' width='20px' xmlns='http://www.w3.org/2000/svg'>
  <path d='M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14' fill-rule='evenodd'></path>
  </svg>
  </span>
  <input class='search__input' name='search' placeholder='Type a phrase to search...'>
  <button class='search__submit' type='submit'>
  Search
  </button>
  </div>
  </form>
  </div>

  <ul class='navigation-list navigation-list_dark'>
  <li class='navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable'>
  <span class='navigation-list__title navigation-hoverable'>
  Free Books
  </span>
  <div class='navigation-dropdown navigation-dropdown_fullwidth'>
  <div class='stories-dropdown'>
  <div class='stories-dropdown__col'>
  <div class='stories-dropdown-title'>
  Genres
  </div>
  <ul class='stories-dropdown-list'>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Sci-Fi Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-scifi' href='/genres/scifi' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-scifi'></div>
  Sci-Fi
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Fantasy Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-fantasy' href='/genres/fantasy' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-fantasy'></div>
  Fantasy
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Adventure Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-adventure' href='/genres/adventure' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-adventure'></div>
  Adventure
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Mystery Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-mystery' href='/genres/mystery' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-mystery'></div>
  Mystery
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Action Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-action' href='/genres/action' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-action'></div>
  Action
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Horror Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-horror' href='/genres/horror' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-horror'></div>
  Horror
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Humor Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-humor' href='/genres/humor' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-humor'></div>
  Humor
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Erotica Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-erotica' href='/genres/erotica' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-erotica'></div>
  Erotica
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Poetry Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-poetry' href='/genres/poetry' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-poetry'></div>
  Poetry
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Other Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-other' href='/genres/other' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-other'></div>
  Other
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Thriller Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-thriller' href='/genres/thriller' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-thriller'></div>
  Thriller
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Romance Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-romance' href='/genres/romance' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-romance'></div>
  Romance
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Children Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-children' href='/genres/children' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-children'></div>
  Children
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Read Drama Stories for Free' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='genre-drama' href='/genres/drama' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_genre-drama'></div>
  Drama
  </a>
  </li>
  </ul>
  </div>
  <div class='stories-dropdown__col'>
  <div class='stories-dropdown-title'>
  Fanfiction
  <a class='stories-dropdown-title__more' data-track-event='navbar-link-clicked' data-track-link='more fandoms' href='/fanfiction' target='_self'>
  More Fanfiction
  </a>
  </div>
  <ul class='stories-dropdown-list'>
  <li class='stories-dropdown-list__item stories-dropdown-list__item_fullwidth'>
  <a alt='Harry Potter' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='fandom harry potter' href='/fanfiction?fandom_name=Harry+Potter&amp;fandom=Harry Potter' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_fandom-harry-potter'></div>
  Harry Potter
  </a>
  </li>
  <li class='stories-dropdown-list__item stories-dropdown-list__item_fullwidth'>
  <a alt='Naruto' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='fandom naruto' href='/fanfiction?fandom_name=Naruto&amp;fandom=Naruto' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_fandom-naruto'></div>
  Naruto
  </a>
  </li>
  <li class='stories-dropdown-list__item stories-dropdown-list__item_fullwidth'>
  <a alt='Supernatural' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='fandom supernatural' href='/fanfiction?fandom_name=Supernatural&amp;fandom=Supernatural' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_fandom-supernatural'></div>
  Supernatural
  </a>
  </li>
  <li class='stories-dropdown-list__item stories-dropdown-list__item_fullwidth'>
  <a alt='Glee' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='fandom glee' href='/fanfiction?fandom_name=Glee&amp;fandom=Glee' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_fandom-glee'></div>
  Glee
  </a>
  </li>
  <li class='stories-dropdown-list__item stories-dropdown-list__item_fullwidth'>
  <a alt='Lord of the rings' class='stories-dropdown-item stories-dropdown-item_simple' data-track-event='navbar-link-clicked' data-track-link='fandom the lord of the rings' href='/fanfiction?fandom_name=Lord+of+the+rings&amp;fandom=Lord of the rings' target='_self'>
  <div class='stories-dropdown-item__icon stories-dropdown-item__icon_fandom-lotr'></div>
  Lord of the rings
  </a>
  </li>
  </ul>
  </div>
  <div class='stories-dropdown__col'>
  <div class='stories-dropdown-title'>
  Trending Topics
  </div>
  <ul class='stories-dropdown-list'>
  <li class='stories-dropdown-list__item'>
  <a alt='Love' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic love' href='/topics/love' target='_self'>
  Love
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Magic' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic magic' href='/topics/magic' target='_self'>
  Magic
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Werewolf' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic werewolf' href='/topics/werewolf' target='_self'>
  Werewolf
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Family' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic family' href='/topics/family' target='_self'>
  Family
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Friendship' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic friendship' href='/topics/friendship' target='_self'>
  Friendship
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Death' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic death' href='/topics/death' target='_self'>
  Death
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Supernatural' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic supernatural' href='/topics/supernatural' target='_self'>
  Supernatural
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Mafia' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic mafia' href='/topics/mafia' target='_self'>
  Mafia
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Fanfiction' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic fanfiction' href='/topics/fanfiction' target='_self'>
  Fanfiction
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Alpha' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic alpha' href='/topics/alpha' target='_self'>
  Alpha
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Short Story' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic short story' href='/topics/short-story' target='_self'>
  Short Story
  </a>
  </li>
  <li class='stories-dropdown-list__item'>
  <a alt='Indian Love Story' class='stories-dropdown-item stories-dropdown-item_hashtag' data-track-event='navbar-link-clicked' data-track-link='topic indian love story' href='/topics/indian-love-story' target='_self'>
  Indian Love Story
  </a>
  </li>
  </ul>
  </div>
  </div>
  </div>

  </li>
  <li class='navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable' id='navigation-list__item-become_a_writer'>
  <span class='navigation-list__title navigation-hoverable'>
  Write
  </span>
  <ul class='navigation-dropdown'>
  <div class='write-story'>
  <button class='write-story__button' id='manage-stories-modal'>
  <span class='write-story__icon'>
  <svg height='21px' width='22px' xmlns='http://www.w3.org/2000/svg'>
  <path d='M4.065 17.823c.159-.147.318-.293.475-.441 1.774-1.66 3.546-3.323 5.323-4.98a.47.47 0 0 1 .285-.125c2.108-.007 4.215-.005 6.322-.004.028 0 .055.013.147.036-.218.24-.395.473-.612.664-2.917 2.558-6.315 4.165-10.227 4.747-.55.083-1.109.122-1.663.18l-.05-.077zm11.233-10.57L22 .817c-.11.647-.194 1.267-.32 1.88a21.7 21.7 0 0 1-1.378 4.267c-.091.208-.19.295-.44.293-1.424-.013-2.848-.006-4.272-.006h-.292zm-8.693 6.484V10.93c0-.918-.01-1.836.008-2.754a.89.89 0 0 1 .187-.527c.61-.717 1.245-1.417 1.875-2.119.19-.21.393-.408.648-.67.013.16.023.231.024.303 0 1.904.003 3.809-.005 5.713 0 .131-.047.298-.138.387-.81.797-1.633 1.58-2.454 2.367-.027.026-.061.046-.145.108zM19.5 8.555c-.281.414-.539.82-.826 1.205-.307.413-.636.813-.971 1.205a.494.494 0 0 1-.325.163c-2.046.01-4.093.006-6.14.004-.028 0-.058-.01-.127-.025.07-.076.12-.141.18-.196.817-.75 1.633-1.501 2.456-2.245a.526.526 0 0 1 .31-.143c1.77-.008 3.542-.005 5.314-.004.027 0 .054.015.13.036zM5.437 9.895c0 1.326-.056 2.656.02 3.979.048.822-.166 1.432-.84 1.946-.467.356-.858.804-1.284 1.21-.013.013-.033.02-.105.059.26-2.555.877-4.968 2.209-7.194zm-2.119 8.732L.844 21 0 20.309l2.48-2.373.838.69zM21.004.067l-10.487 9.944v-.326c0-1.836.004-3.673-.007-5.51-.001-.224.08-.351.26-.478C13.415 1.853 16.324.62 19.568.155c.467-.067.938-.104 1.408-.155l.03.068z' fill-rule='evenodd'></path>
  </svg>
  </span>
  Write or Upload Story
  </button>
  </div>
  <ul class='navigation-dropdown__sublist'>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='writers bootcamp' href='/writers-bootcamp' id='navigation-dropdown__link-writers_bootcamp' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  Novel Writing Boot Camp
  </div>
  <div class='navigation-dropdown__subtitle'>
  The fundamentals of fiction writing by Bryan Thomas Schmidt
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='winners' href='/inkitt-winners' id='' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  Winners
  </div>
  <div class='navigation-dropdown__subtitle'>
  Contest Winners
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='writers blog' href='/writersblog/' id='' target='_blank'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  The Writer&#39;s Blog
  </div>
  <div class='navigation-dropdown__subtitle'>
  Learn about the craft of writing
  </div>
  </a>
  </li>
  </ul>
  </ul>
  </li>
  <li class='navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable'>
  <span class='navigation-list__title navigation-hoverable'>
  Community
  </span>
  <ul class='navigation-dropdown'>
  <div class='navigation-contests'>
  <div class='stories-dropdown-title'>
  Featured Groups
  </div>
  <ul class='stories-dropdown-list'>
  <li class='stories-dropdown-list__item stories-dropdown-list__item_fullwidth'>
  <a class='stories-dropdown-item' data-track-event='navbar-link-clicked' data-track-link='/groups/Community' href='/groups/Community' target='_self'>
  <img class='stories-dropdown-item__icon' loading='lazy' src='https://cdn-gcs.inkitt.com/uploads/group_category/1006/8df533eb-fb78-4000-88c3-3ba18aedcfe8.jpg'>
  <div class='stories-dropdown-item__info'>
  Inkitt Community
  <div class='stories-dropdown-item__footer'>
  Welcome to Inkitt!
  </div>
  </div>
  </a>
  </li>
  </ul>

  </div>
  <ul class='navigation-dropdown__sublist'>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='groups' href='/groups' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  Groups
  </div>
  <div class='navigation-dropdown__subtitle'>
  Engage with fellow authors &amp; writers
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='guidelines' href='/guidelines' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  Community Guidelines
  </div>
  <div class='navigation-dropdown__subtitle'>
  Discover the values of our community
  </div>
  </a>
  </li>
  </ul>
  </ul>
  </li>
  <li class='navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable'>
  <a class='navigation-list__title navigation-hoverable' data-track-event='navbar-link-clicked' data-track-link='book-store' href='https://galatea.com' target='_blank'>
  Galatea
  </a>
  </li>
  <li class='navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable'>
  <span class='navigation-list__title navigation-hoverable'>
  Writing Contests
  </span>
  <ul class='navigation-dropdown'>
  <ul class='navigation-dropdown__sublist navigation-dropdown__contests'>
  <li class='navigation-dropdown__item'>
  <a class='contest-dropdown-item navigation-dropdown__link' href='/historical-romance-2024' target='_self'>
  <img class='stories-dropdown-item__icon' src='https://cdn-gcs.inkitt.com/contestpictures/539c6e6a-ddd8-4d0b-a5fc-3f20e1a148b8.png'>
  <div class='stories-dropdown-item__info'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  Historical Romance: Love Through the Ages
  </div>
  <div class='navigation-dropdown__subtitle'>
  Romance Contest
  </div>
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='contest-dropdown-item navigation-dropdown__link' href='/fantasy-worlds-2024' target='_self'>
  <img class='stories-dropdown-item__icon' src='https://cdn-gcs.inkitt.com/contestpictures/eb4f6e87-1f46-4b85-9b67-a1abec95edf8.png'>
  <div class='stories-dropdown-item__info'>
  <div class='navigation-dropdown__title navigation-dropdown__title_bold'>
  Fantasy Worlds: Beyond Imagination
  </div>
  <div class='navigation-dropdown__subtitle'>
  Fantasy Contest
  </div>
  </div>
  </a>
  </li>
  </ul>
  </ul>
  </li>

  <li class='navigation-list__item navigation-list__item_expandable js-navigation-list__item-expandable'>
  <a class='navigation-list__title navigation-hoverable' data-track-event='navbar-link-clicked' data-track-link='/author-subscription' href='/author-subscription' target='_self'>
  Author Subscription
  </a>
  </li>
  </ul>
  </div>

  </div>
  <div class='navigation__right'>
  <div class='navigation-group'>
  <ul class='navigation-list navigation-actions navigation-list_dark'>
  <li class='navigation-actions__item navigation-show_desktop'>
  <div class='search js-search'>
  <button class='search__expander navigation-hoverable' data-track-source='Search Bar'>
  <span class='search__icon'>
  <svg height='19px' width='20px' xmlns='http://www.w3.org/2000/svg'>
  <path d='M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14' fill-rule='evenodd'></path>
  </svg>
  </span>
  Search
  </button>
  <form class='js-search-form'>
  <div class='search__inputWrapper'>
  <span class='search__icon'>
  <svg height='19px' width='20px' xmlns='http://www.w3.org/2000/svg'>
  <path d='M2.67 8.676c-.014 3.325 2.717 6.066 6.086 6.067 3.37.002 6.106-2.652 6.12-6.03.013-3.369-2.72-6.046-6.084-6.067-3.35-.02-6.108 2.696-6.122 6.03M20 16.886c-.521.516-1.6 1.597-2.122 2.114-.032-.029-.074-.064-.112-.102-1.098-1.086-2.196-2.17-3.29-3.26-.111-.112-.179-.128-.307-.018-.95.807-1.756 1.083-2.958 1.427-1.237.354-2.495.45-3.77.237-2.85-.477-4.982-1.98-6.386-4.472A8.086 8.086 0 0 1 .033 8.058C.29 5.092 1.717 2.818 4.257 1.25A8.262 8.262 0 0 1 9.377.03c3.168.26 5.53 1.798 7.104 4.522.609 1.054.932 2.205 1.033 3.42.163 1.959-.001 3.486-1.058 5.141-.076.119-.068.19.033.29 1.13 1.11 2.253 2.227 3.378 3.342.044.044.086.09.133.14' fill-rule='evenodd'></path>
  </svg>
  </span>
  <input class='search__input' name='search' placeholder='Search...'>
  </div>
  </form>
  </div>

  </li>
  <li class='navigation-actions__item navigation-hoverable'>
  <div class='navigation-language js-select-language'>
  <div class='navigation-language__current-language'>
  en
  <i class='navigation-language__arrow icon-down-dir'></i>
  </div>
  <div class='navigation-dropdown navigation-dropdown_thin navigation-dropdown_origin-right'>
  <ul class='navigation-dropdown__sublist'>
  <li class='navigation-dropdown__item navigation-dropdown__item_active'>
  <a class='navigation-dropdown__link set-app-language' data-language='en' data-track-event='navbar-link-clicked' data-track-link='locale-en' href='' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__language_code_name'>
  <div>
  <img class='navigation-dropdown__language_flag' src='https://cdn-firebase.inkitt.com/packs/media/language_flags/en-e013135e.png'>
  <span>english</span>
  <span class='navigation-dropdown__language_code'>(en)</span>
  </div>
  <div>
  <span class='active_language'>
  <svg fill='none' height='10px' viewBox='0 0 14 10' width='14px' xmlns='http://www.w3.org/2000/svg'>
  <path d='M12.3333 1L6.40737 8.33333L1.66663 4.31183' stroke='black' stroke-linecap='round' stroke-linejoin='round' stroke-width='1.5'></path>
  </svg>
  </span>
  </div>
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link set-app-language' data-language='es' data-track-event='navbar-link-clicked' data-track-link='locale-es' href='' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__language_code_name'>
  <div>
  <img class='navigation-dropdown__language_flag' src='https://cdn-firebase.inkitt.com/packs/media/language_flags/es-937fee20.png'>
  <span>español</span>
  <span class='navigation-dropdown__language_code'>(es)</span>
  </div>
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link set-app-language' data-language='de' data-track-event='navbar-link-clicked' data-track-link='locale-de' href='' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__language_code_name'>
  <div>
  <img class='navigation-dropdown__language_flag' src='https://cdn-firebase.inkitt.com/packs/media/language_flags/de-d99569d2.png'>
  <span>deutsch</span>
  <span class='navigation-dropdown__language_code'>(de)</span>
  </div>
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link set-app-language' data-language='fr' data-track-event='navbar-link-clicked' data-track-link='locale-fr' href='' target='_self'>
  <div class='navigation-dropdown__title navigation-dropdown__language_code_name'>
  <div>
  <img class='navigation-dropdown__language_flag' src='https://cdn-firebase.inkitt.com/packs/media/language_flags/fr-461e44b8.png'>
  <span>français</span>
  <span class='navigation-dropdown__language_code'>(fr)</span>
  </div>
  </div>
  </a>
  </li>
  </ul>
  </div>
  </div>

  </li>
  <li class='navigation-actions__item'>
  <button class='navigation-button js-login-signup-anchor navigation-button_dark' data-next-state='signin'>
  sign in
  </button>
  </li>
  <li class='navigation-actions__item navigation-show_desktop'>
  <button class='navigation-button js-login-signup-anchor navigation-button_dark' data-next-state='signup'>
  sign up
  </button>
  </li>

  <li class='navigation-actions__item navigation-show_desktop navigation-hoverable'>
  <div class='navigation-more js-more-links'>
  <i class='navigation-more__dots icon-dot-3'></i>
  <div class='navigation-dropdown navigation-dropdown_thin navigation-dropdown_origin-right'>
  <ul class='navigation-dropdown__sublist'>
  <li class='navigation-dropdown__item'>
  <span class='navigation-dropdown__link js-how-it-works-anchor'>
  <div class='navigation-dropdown__title'>
  How it works
  </div>
  </span>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Inkitt Publishing' href='https://www.inkitt.com/writersblog/how-inkitt-publishes-your-books-from-preparation-to-promotion' target='_self'>
  <div class='navigation-dropdown__title'>
  Inkitt Publishing
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Inkitt Winners' href='/inkitt-winners' target='_self'>
  <div class='navigation-dropdown__title'>
  Inkitt Winners
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Badges' href='/badges' target='_self'>
  <div class='navigation-dropdown__title'>
  Badges
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Guidelines' href='/guidelines' target='_self'>
  <div class='navigation-dropdown__title'>
  Guidelines
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Support' href='https://inkitt.zendesk.com/hc/en-us' target='_self'>
  <div class='navigation-dropdown__title'>
  Support
  </div>
  </a>
  </li>
  </ul>
  <ul class='navigation-dropdown__sublist'>
  <li class='navigation-dropdown__item'>
  <a alt='Facebook' class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Facebook' href='https://www.facebook.com/inkitt' target='_blank'>
  <div class='navigation-dropdown__title'>
  <span class='social-icon icon-facebook-1'></span>
  Facebook
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a alt='Twitter' class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Twitter' href='https://www.twitter.com/inkitt' target='_blank'>
  <div class='navigation-dropdown__title'>
  <span class='social-icon icon-twitter'></span>
  Twitter
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a alt='Blog' class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='Blog' href='/writersblog/' target='_blank'>
  <div class='navigation-dropdown__title'>
  <span class='social-icon icon-blogger'></span>
  Blog
  </div>
  </a>
  </li>
  </ul>
  <ul class='navigation-dropdown__sublist'>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='jobs' href='/jobs' target='_self'>
  <div class='navigation-dropdown__title'>
  Jobs
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='credits' href='/credits' target='_self'>
  <div class='navigation-dropdown__title'>
  Credits
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='terms' href='/terms' target='_self'>
  <div class='navigation-dropdown__title'>
  Terms
  </div>
  </a>
  </li>
  <li class='navigation-dropdown__item'>
  <a class='navigation-dropdown__link' data-track-event='navbar-link-clicked' data-track-link='imprint' href='/imprint' target='_self'>
  <div class='navigation-dropdown__title'>
  Imprint
  </div>
  </a>
  </li>
  </ul>
  <div class='navigation-more__note'>
  <span class='icon-heart'></span>
  Inked with love
  </div>
  </div>
  </div>

  </li>
  <li class='navigation-actions__item navigation-hide_desktop'>
  <button class='navigation-expander navigation-expander_dark' id='js-navigation-expander'>
  <span class='navigation-expander__icon'></span>
  </button>
  </li>
  </ul>
  </div>

  </div>
  </nav>


  <div id='reading-chapter-progress-container' props='{&quot;read_progress&quot;:[{&quot;percentage&quot;:0.9998863765481195,&quot;status&quot;:&quot;read&quot;},{&quot;percentage&quot;:3.2212248608112715,&quot;status&quot;:&quot;read&quot;},{&quot;percentage&quot;:3.2098625156232248,&quot;status&quot;:&quot;current&quot;},{&quot;percentage&quot;:3.2496307237813884,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.033746165208499,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1814566526531074,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.962617884331326,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.090557891148733,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1558913759800022,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.207021929326213,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1985001704351776,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.417225315305079,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.763776843540507,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.2013407567321894,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.073400749914782,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.596182252016816,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5081240768094535,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5819793205317576,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5564140438586525,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.010907851380525,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.1530507896829905,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.8518350187478694,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.596182252016816,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.7098057038972843,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.50244290421543,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.050676059538689,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.5336893534825586,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.848994432450858,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.5335757300306785,&quot;status&quot;:&quot;notread&quot;}]}'></div>
  <div class='page StoryPage'>
  <div class='story-page story-id-1176584' id='page-internal'>
  <div class='story-horizontal-cover' data-cover-url='https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg' data-is-test='false' data-summary='Parker was the only girl in her family. Her mother was convinced she was a boy so had decided her name while she was in the womb. Her mother and her three brothers all called her Parker even before she was born so the name stuck.

  Parker takes care of her family. She cooks and cleans for her brothers when her parents are off travelling the world. At 18 she has never so much as kissed a boy let alone had a boyfriend. She doesn&#39;t have time for it between studying, working and looking after her brothers. She didn&#39;t mind, that&#39;s what families did apparently.

  As her graduation draws near her parents and brothers promise to be there. She is excited to finally be finishing high school. She had been accepted to university on the other side of the country but was reluctant to accept because it would mean leaving behind her family.

  Parker&#39;s brothers are working in the family business since there dad retired to travel with there mother. Leon is 26, Jude is 23 and Tanner is 22. They are play boys and are loving life. They have no responsibilitIes at home because Parker takes care of them. They forget all about her graduation until the day after it occurs as do her parents. They vow to make it up to her but when she doesn&#39;t come home they know they have made the biggest mistake of there lives.

  Parker is hurt by her family. Her brothers friend, who had seen everything that had been ha' data-test-type='titles' data-title='Finding me'>
  <div class='story-horizontal-cover__back story-horizontal-cover__back_blurred' itemprop='image' style='background-image: url(&#39;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg&#39;)'></div>
  <div class='story-horizontal-cover__front-wrap'>
  <div id='image-zoom' props='{&quot;cover&quot;:{&quot;url&quot;:&quot;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg&quot;},&quot;storyTitle&quot;:&quot;Finding me&quot;,&quot;className&quot;:&quot;story-horizontal-cover__front&quot;}'></div>
  </div>
  </div>


  <div class='container'>
  <div class='row no-gutters'>
  <div class='col-2 story-left-side offset-1'>
  <div class='showed-block'>
  <div class='sticky-left-pan' style='display: none'></div>
  <div id='like-story-button'></div>
  <button class='button show-reading-lists-button' id='show-reading-lists-button'>
  <i class='icon-white icon-bookmark'></i>
  <span class='big-screen'>
  Add to Reading List
  </span>
  <span class='small-screen'>
  Reading List
  </span>
  </button>
  <div id='reading-lists-block-container' props='{&quot;storyId&quot;:1176584}'></div>
  <div style='position: relative'>
  <div class='write-review-tooltip' style='display: none'>
  <div class='arrow_box'></div>
  kyliet would love your feedback! Got a few minutes to write a review?
  <i class='icon-cancel-1'></i>
  </div>
  <a class='button create-review-button' href='/stories/drama/1176584/reviews/new'>
  Write a Review
  </a>
  </div>
  <div id='sharing-widget-container' props='{&quot;facebookIcon&quot;:true,&quot;includeTumblr&quot;:true,&quot;name&quot;:&quot;Read Finding me for free on Inkitt.&quot;,&quot;shareLocation&quot;:&quot;storypage&quot;,&quot;shareUrl&quot;:&quot;https://www.inkitt.com/stories/drama/1176584&quot;,&quot;storyId&quot;:1176584,&quot;disabled&quot;:false}'></div>
  <div id='report-story-button'></div>
  <div id='custom-styling-container'></div>
  </div>
  </div>
  <div class='col-6 story-middle-column'>
  <header class='story-header' data-profile-tracking-source='Story'>
  <h1 class='story-title story-title--small'>
  Finding me
  </h1>
  <div class='author-block'>
  <a class='author-link' data-cta='Profile Picture' href='/kyliet' track-profile-click='true'>
  <img class='profile-picture' src='https://cdn-gcs.inkitt.com/profilepictures/small_17b78a1c8e8d5aadf4911fce06fe077f.jpg'>
  </a>
  <div class='block-1'>
  <a class='author-link' data-cta='Username' href='/kyliet' track-profile-click='true'>
  <span class='name' id='storyAuthor'>kyliet</span>
  </a>
  <a class='stories-count author-link' data-cta='Story Count' href='/kyliet' track-profile-click='true'>
  17 stories
  </a>
  </div>
  <div class='block-2' id='follow-button-container' props='{&quot;user&quot;:{&quot;id&quot;:3028573,&quot;is_followed&quot;:false}}'></div>
  </div>
  <p class='all-rights-reserved'>
  All Rights Reserved ©
  </p>
  </header>
  <article class='default-style' id='story-text-container' style='font-size: 22px'>
  <h2 class='chapter-head-title'>
  Chapter 1
  </h2>
  <div class='' style='position: relative'>
  <div class='story-page-text' id='chapterText'>
  <p data-content="4049905067">Parker stood when her name was announced and headed to the microphone. Even her peers could see that something had changed in Parker. Her smile wasn't her true smile and no one knew why. Parker read her speech and did what she was suppose to do while starring at the empty seats her family should of occupied. At the part in her speech where she was suppose to thank her family she stopped.</p><p data-content="209879444"><br></p><p data-content="4102576269">Parker looked up from her paper and stopped reading. "You know what. I want to say to everyone, we did this ourselves, we got here on our own. Others have supported us but they couldn't do it for us. We did it, we should be thanking ourselves for all we have achieved because as they saying goes, you can lead a horse to water but can not force them to drink. So instead of thanking friends, family that couldn't be bothered with me, I thank me and I promise myself this. I will find me, I will find the real Parker Jones and where I belong because it's not here. Thank you" Parker said before going to sit back down.</p><p data-content="209879444"><br></p><p data-content="3614281206">William was shocked, he turned to Parker to see she now held herself differently. She wasn't looking at the empty seats at all, she was watching her classmates cheering at what she had said while the teachers tried to quieten them down. He shook his head slightly amused at what Parker had just done and how she finally called her family out, even if they weren't here to see it.</p><p data-content="209879444"><br></p><p data-content="2372915048">The rest of the ceremony went on and as Parker's name was called to be presented with an award, Mrs Andre beamed at her achievements which were read along with announcing how Parker had got a full scholarship to uni to study and wishing her well. William was presenting the award and couldn't be prouder of the girl. William had seen Parker grow up and treated her like a little sister. William was an only child so loved spending time with the Jones'. "I'm so happy for you Parker" he whispered when he pulled her into a hug.</p><p data-content="209879444"><br></p><p data-content="2754375482">Parker smiled for the mandatory photo but again the smile didn't reach her eyes at all. She was hurt and angry and felt let down. "Parker you deserve this. Celebrate your victory" William whispered and tickled her side until finally a genuine smile was on her face. The cameras flashed just at the right moment and William also had a huge smile on his face. He was glad he got to share this moment with Parker and that she wasn't alone even though her family had let her down.</p><p data-content="209879444"><br></p><p data-content="3151720877">As the ceremony drew to a close Parker threw her hat up with her classmates and wished she was far away from her family. Parker moved around thanking her teachers and taking pictures with some friends. All she wanted to do was go and hide in her room and pretend today never happened.</p><p data-content="209879444"><br></p><p data-content="3094691873">William tried to get to Parker but was continually stopped by different people wanting to talk. William was going to make tonight special for Parker if he could just get to her. Most of the girls in the class had flowers or a teddy but not Parker, that didn't sit well with William at all. He didn't have romantic feelings for the girl, he genuinely saw her as a little sister.</p><p data-content="209879444"><br></p><p data-content="2020906599">When William managed to get away he couldn't find Parker at all. He was upset with himself that he couldn't make tonight all about celebrating her so decided to head out. When he got to his car he saw Parker sitting at the bus stop and he knew what he had to do. William called a local restaurant and booked a table while asking the manager who he knew, to grab a bunch of flowers explaining his little sister has just graduated. The woman, Nancy, promised to organise it all.</p><p data-content="209879444"><br></p><p data-content="968688839">William pulled up in front of the bus stop and rolled the window down. "Little Jones, hop in. I am taking you out to dinner to celebrate" William called out. Parker just shook her head no, she just wanted to curl up in a ball at home. She didn't know if her family were hurt or not. "Come on Parker, you know you want to" William coaxed. Parked again shook her head no, she honestly just wanted to go home.</p><p data-content="209879444"><br></p><p data-content="1207483251">After a few more minutes of William trying to coax Parker, she finally agreed getting in the car. She wouldn't admit it was because the bus was cancelled and she didn't want to be out in public though. "Ok Parks, I'm taking you to dinner to celebrate and you are going to tell me about this uni offer" William said before driving to the restaurant.</p><p data-content="209879444"><br></p><p data-content="3669035800">As Parker and William pulled into the restaurant she was smiling again. William was a goof ball and couldn't help but crack jokes all the way there. He saw the hurt in Parker's eyes and he didn't like it. William still hadn't had a chance to message Leon about ditching his sister for a piece of arse. "Hey William, please don't say anything to my brother" Parker stated as she stepped out of the car.</p><p data-content="209879444"><br></p><p data-content="2547764428">William lead Parker into the restaurant wanting to find out why she didn't want her family to know. "You don't want your family knowing you graduated?" William asked. Maybe Parker hadn't of wanted them there. "I don't want them knowing about uni. I haven't decided if I'm going" Parker corrected before adding, "they all know about me graduating, I'm just not important enough for them to attend".</p><p data-content="209879444"><br></p><p data-content="2006529293">William was stunned but didn't say a thing to Parker. He wanted tonight to be about her achievements. As they got into the restaurant Nancy was waiting with a bunch of bright yellow and orange Gerber's and a little graduation bear. "Hey William this must by miss Parker the graduate. Well done" Nancy beamed handing the teddy and flowers to Parker. Parker couldn't stop the tears, this is exactly what she wanted from her family and here a stranger and her brothers friend, were giving her what her family hadn't bothered to do. "Thank you" Parker mumbled out wiping her eyes hoping no one noticed. William did and he was glad he could do something special but also annoyed that he had to step up because her family couldn't. William reminded himself that tonight was about Parker and making it special for her.</p>
  </div>
  </div>
  </article>
  </div>
  <div class='col-3 story-right-side'>
  <div class='showed-block'>
  <div class='sticky-right-pan'>
  <div class='chapters-list' style='display: none'>
  <div class='current-chapter'>
  <i class='icon-angle-down'></i>
  <strong>Chapters</strong>
  <div class='chapter-name'>3. Chapter 1</div>
  </div>
  <ul class='nav nav-list chapter-list-dropdown'>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/1"><span class='chapter-nr'>
  1
  </span>
  <span class='chapter-title'>
  Authors note
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/2"><span class='chapter-nr'>
  2
  </span>
  <span class='chapter-title'>
  Prolgue
  </span>
  </a></li>
  <li class='active'>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/3"><span class='chapter-nr'>
  3
  </span>
  <span class='chapter-title'>
  Chapter 1
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/4"><span class='chapter-nr'>
  4
  </span>
  <span class='chapter-title'>
  Chapter 2
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/5"><span class='chapter-nr'>
  5
  </span>
  <span class='chapter-title'>
  Chapter 3
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/6"><span class='chapter-nr'>
  6
  </span>
  <span class='chapter-title'>
  Chapter 4
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/7"><span class='chapter-nr'>
  7
  </span>
  <span class='chapter-title'>
  Chapter 5
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/8"><span class='chapter-nr'>
  8
  </span>
  <span class='chapter-title'>
  Chapter 6
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/9"><span class='chapter-nr'>
  9
  </span>
  <span class='chapter-title'>
  Chapter 7
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/10"><span class='chapter-nr'>
  10
  </span>
  <span class='chapter-title'>
  Chapter 8
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/11"><span class='chapter-nr'>
  11
  </span>
  <span class='chapter-title'>
  Chapter 9
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/12"><span class='chapter-nr'>
  12
  </span>
  <span class='chapter-title'>
  Chapter 10
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/13"><span class='chapter-nr'>
  13
  </span>
  <span class='chapter-title'>
  Chapter 11
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/14"><span class='chapter-nr'>
  14
  </span>
  <span class='chapter-title'>
  Chapter 12
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/15"><span class='chapter-nr'>
  15
  </span>
  <span class='chapter-title'>
  Chapter 13
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/16"><span class='chapter-nr'>
  16
  </span>
  <span class='chapter-title'>
  Chapter 14
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/17"><span class='chapter-nr'>
  17
  </span>
  <span class='chapter-title'>
  Chapter 15
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/18"><span class='chapter-nr'>
  18
  </span>
  <span class='chapter-title'>
  Chapter 16
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/19"><span class='chapter-nr'>
  19
  </span>
  <span class='chapter-title'>
  Chapter 17
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/20"><span class='chapter-nr'>
  20
  </span>
  <span class='chapter-title'>
  Chapter 18
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/21"><span class='chapter-nr'>
  21
  </span>
  <span class='chapter-title'>
  Chapter 19
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/22"><span class='chapter-nr'>
  22
  </span>
  <span class='chapter-title'>
  Chapter 20
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/23"><span class='chapter-nr'>
  23
  </span>
  <span class='chapter-title'>
  Chapter 21
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/24"><span class='chapter-nr'>
  24
  </span>
  <span class='chapter-title'>
  Chapter 22
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/25"><span class='chapter-nr'>
  25
  </span>
  <span class='chapter-title'>
  Chapter 23
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/26"><span class='chapter-nr'>
  26
  </span>
  <span class='chapter-title'>
  Chapter 24
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/27"><span class='chapter-nr'>
  27
  </span>
  <span class='chapter-title'>
  Chapter 25
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/28"><span class='chapter-nr'>
  28
  </span>
  <span class='chapter-title'>
  Chapter 26
  </span>
  </a></li>
  <li class=''>
  <a class="chapter-link" rel="nofollow" href="/stories/drama/1176584/chapters/29"><span class='chapter-nr'>
  29
  </span>
  <span class='chapter-title'>
  Epilogue
  </span>
  </a></li>
  </ul>
  </div>
  </div>
  </div>
  </div>
  </div>
  <div class='row no-gutters'>
  <div class='col-2 story-left-side'></div>
  <div class='col-8 story-middle-column'>
  <a class='inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn' href='' id='continue-reading-btn'>Continue Reading</a>
  </div>
  <div class='col-2 story-right-side'></div>
  </div>
  <div class='row no-gutters'>
  <div class='col-2 story-left-side'></div>
  <div class='col-8 story-middle-column'>
  <article class='default-style' id='story-text-container' style='font-size: 22px'>
  </article>
  <a class="inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn" target="_self" id="next-chapter-btn" href="/stories/drama/1176584/chapters/4">Next Chapter</a>
  <div id='story-post-chapter-reviews'></div>
  <div id='story-comments'></div>
  <div id='author-follow-modal'></div>
  </div>
  <div class='col-2 story-right-side'></div>
  </div>
  </div>
  <div id='story-contest-bar-container' props='{&quot;isAuthorOfCurrentStory&quot;:false}'></div>
  </div>
  </div>
  <div id='inlineCommentsSidebar'></div>
  <div class='non-js-popup-overlay non-js-popup-overlay_dark' id='login-signup-popup' role='dialog' tabindex='-1'>
  <div class='modal login-signup-modal'>
  <a class='popup-cancel js-close-popup' href='#'></a>
  <div class='modal-dialog'>
  <div class='modal-dialog__close'>
  <a class='popup-cancel-icon js-close-popup' href='#'></a>
  </div>
  <div class='modal-content'>
  <div class='login-signup-wrapper js-login-signup-signin'>
  <div class='login-signup-inner'>
  <header class='login-signup__title'>
  Sign in to Inkitt
  </header>

  <form class='signup-input-fields-wrapper' name='logInForm'>
  <input class='signin-email' name='username' placeholder='E-mail or Username' type='text'>
  <input name='password' placeholder='Password' type='password'>
  <button class='login-signup-btn login-signup-btn_dark' type='submit'>
  <i class='login-signup-btn__icon icon-spin5 spinner animate-spin feedback-spinner'></i>
  <span class='login-btn-text'>
  Sign in
  </span>
  </button>
  <div class='error-wrapper-small js-login-error'></div>
  </form>
  <a class='link-small js-login-signup-switcher' data-next-state='forgot-password'>
  Forgot your password?
  </a>
  <div class='or-divider'>
  <span>
  Or
  </span>
  </div>
  <div class='login-signup-social'>
  <div class='google-login-btn' id='google-login-btn'></div>
  <div class='error-wrapper-small js-login-social-error' id='google-login-error'></div>
  </div>

  <div class='login-signup-subtitle'>
  You can also
  <a class='js-login-signup-switcher' data-next-state='signup'>
  sign up
  </a>
  </div>
  </div>

  </div>
  <div class='login-signup-wrapper js-login-signup-signup'>
  <div class='login-signup-inner'>
  <header class='login-signup__title'>
  Sign up with email
  </header>

  <form class='signup-input-fields-wrapper' name='signUpForm'>
  <input class='signup-email' name='email' placeholder='Enter your E-mail' type='text'>
  <input class='signup-username' name='username' placeholder='Pick a Username' type='text'>
  <input name='password' placeholder='Pick a Password' type='password'>
  <div class='birthday-container'>
  <label for='birthday_input'>
  Pick Your Birth Date
  </label>
  <div class='birthday-input-wrapper'>
  <input date-value='Y-m-d' id='birthday_input' name='birthday' type='text' value=''>
  </div>
  </div>

  <div class='error-wrapper-small js-login-error'></div>
  <button class='login-signup-btn login-signup-btn_dark' type='submit'>
  <i class='login-signup-btn__icon icon-spin5 spinner animate-spin feedback-spinner'></i>
  <span class='login-btn-text'>
  Sign up
  </span>
  </button>
  </form>
  <div class='have-an-account-subtitle login-signup-terms'>
  By signing up on Inkitt, you agree to our
  <a target="_blank" href="/terms">Terms of Service</a>
  and
  <a target="_blank" href="/privacy">Privacy Policy</a>
  </div>
  <div class='have-an-account-subtitle login-signup-subtitle'>
  Have an account?
  <a class='js-login-signup-switcher' data-next-state='signin'>
  Sign in
  </a>
  </div>
  </div>

  </div>
  <div class='login-signup-wrapper js-login-signup-forgot-password'>
  <div class='login-signup-inner login-signup-forgot-password'>
  <header class='login-signup__title'>
  Reset Password
  </header>

  <form class='signup-input-fields-wrapper' name='resetPasswordForm'>
  <input class='resetpassword-email' name='email' placeholder='E-mail address' type='text'>
  <button class='login-signup-btn login-signup-btn_dark' type='submit'>
  <i class='icon-spin5 spinner animate-spin feedback-spinner'></i>
  Reset Password
  </button>
  <div class='error-wrapper-small js-login-error'></div>
  <div class='password-reset-message js-password-reset-message'></div>
  </form>
  <a class='link-small right js-login-signup-switcher' data-next-state='signin'>
  Cancel
  </a>
  </div>

  </div>
  </div>
  </div>
  </div>
  </div>

  <div id='continue-reading-popup'></div>
  <script>
    window.storyPage = true;
  </script>
  <div class='footerLinksSection'>
  <section class='lighthouseFooterLinks'>
  <div class='lighthouseFooterLinks_wrap'>
  <div class='lighthouseFooterLinks_column'>
  <div class='lighthouseFooterLinks_title'>Galatea Stories</div>
  <ul class='lighthouseFooterLinks_links'>
  <li class='lighthouseFooterLinks_link'>
  <a href="https://galatea.com/en/s/77">The Millennium Wolves</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a href="https://galatea.com/en/s/251">Kidnapped by My Mate</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a href="https://galatea.com/en/s/1386">When the Night Falls</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a href="https://galatea.com/en/s/1222">Keily</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a href="https://galatea.com/en/s/335">The Lycan&#39;s Queen</a>
  </li>
  </ul>
  </div>
  <div class='lighthouseFooterLinks_column'>
  <div class='lighthouseFooterLinks_title'>Newest Collections</div>
  <ul class='lighthouseFooterLinks_links'>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/witches">Witches</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/suspence">Suspence</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/supernatural">Supernatural</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/f-m">F-M</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/paranormal">Paranormal</a>
  </li>
  </ul>
  </div>
  <div class='lighthouseFooterLinks_column'>
  <div class='lighthouseFooterLinks_title'>Popular Collections</div>
  <ul class='lighthouseFooterLinks_links'>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/love">Love</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/magic">Magic</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/werewolf">Werewolf</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/family">Family</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/friendship">Friendship</a>
  </li>
  </ul>
  </div>
  <div class='lighthouseFooterLinks_column'>
  <div class='lighthouseFooterLinks_title'>Other Collections</div>
  <ul class='lighthouseFooterLinks_links'>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/philosophic">Philosophic</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/billioniare">Billioniare</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/bonding">Bonding</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/romantic-short-story">Romantic Short Story</a>
  </li>
  <li class='lighthouseFooterLinks_link'>
  <a target="_self" href="https://www.inkitt.com/topics/crime-fighting">Crime Fighting</a>
  </li>
  </ul>
  </div>
  </div>
  </section>
  <div class='non-js-popup-overlay' id='how-it-works-popup' role='dialog' tabindex='-1'>
  <div class='modal how-it-works-modal'>
  <span class='popup-cancel js-close-popup'></span>
  <div class='modal-dialog'>
  <div class='modal-dialog__close'>
  <span class='popup-cancel-icon js-close-popup'></span>
  </div>
  <div class='modal-content modal-content_light'>
  <header class='modal-content__header'>
  <h2 class='modal-content__title'>
  How It Works
  </h2>
  <p class='modal-content__subtitle'>
  Inkitt’s mission is to discover talented writers and turn them into globally successful authors.
  </p>
  </header>
  <div class='modal-content__body'>
  <ol class='howitworks-steps'>
  <li class='howitworks-steps__item'>
  <div class='howitworks-step'>
  <div class='howitworks-step__counter'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/write-e83f00b9.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/write@2x-8cf841fb.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/write@3x-f9a21243.png 3x'>
  </div>
  <div class='howitworks-step__title'>
  Writers Write
  <span class='howitworks-step__arrow'></span>
  </div>
  <p class='howitworks-step__desc'>
  Authors can write and upload their manuscripts on Inkit for free and writers retain 100% of their copyrights whilst writing on Inkitt
  </p>
  </div>
  </li>
  <li class='howitworks-steps__item'>
  <div class='howitworks-step'>
  <div class='howitworks-step__counter'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/explore-a0334c35.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/explore@2x-d63d7175.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/explore@3x-675d98dc.png 3x'>
  </div>
  <div class='howitworks-step__title'>
  Readers Discover
  <span class='howitworks-step__arrow'></span>
  </div>
  <p class='howitworks-step__desc'>
  Readers can read all books for free, without any ads and give the authors feedback.
  </p>
  </div>
  </li>
  <li class='howitworks-steps__item'>
  <div class='howitworks-step'>
  <div class='howitworks-step__counter'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/publish-9c15ef5f.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/publish@2x-3c30dd6d.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/publish@3x-885a55be.png 3x'>
  </div>
  <div class='howitworks-step__title'>
  We Publish
  <span class='howitworks-step__arrow'></span>
  </div>
  <p class='howitworks-step__desc'>
  Books that perform well based on their reader engagement are published on our Galatea app.
  </p>
  </div>
  </li>
  </ol>
  </div>
  <div class='modal-content__footer'>
  <ul class='brands-list'>
  <li class='brands-list__item'>
  <div class='brands-list-brand'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/financial-times-363dc69c.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/financial-times@2x-da658ddd.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/financial-times@3x-db8ae23d.png 3x'>
  </div>
  </li>
  <li class='brands-list__item'>
  <div class='brands-list-brand'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/theguardian-79eff73f.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/theguardian@2x-529cd7ac.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/theguardian@3x-87c8fd04.png 3x'>
  </div>
  </li>
  <li class='brands-list__item'>
  <div class='brands-list-brand'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/bookseller-ca9305c2.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/bookseller@2x-f5a8cdf3.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/bookseller@3x-b285b288.png 3x'>
  </div>
  </li>
  <li class='brands-list__item'>
  <div class='brands-list-brand'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/bbc-c26fe5e1.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/bbc@2x-8666354d.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/bbc@3x-10dbd86a.png 3x'>
  </div>
  </li>
  <li class='brands-list__item'>
  <div class='brands-list-brand'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/frontpage/gizmodo-a1338237.png' srcset='https://cdn-firebase.inkitt.com/packs/media/frontpage/gizmodo@2x-ad14255c.png 2x, https://cdn-firebase.inkitt.com/packs/media/frontpage/gizmodo@3x-60d746d9.png 3x'>
  </div>
  </li>
  </ul>
  </div>
  </div>
  </div>
  </div>
  </div>


  </div>

    <div id='fb-root'></div>
    <script type="text/javascript">
      window.fbAsyncInit = function() {
        FB.init({
          appId: '492061657507324',
          status: true,
          cookie: true,
          xfbml: true,
          version: 'v14.0'
        });
      };

      (function(d, s, id){
        var js, fjs = d.getElementsByTagName(s)[0];
        if (d.getElementById(id)) {return;}
        js = d.createElement(s); js.id = id;
        js.src = "https://connect.facebook.net/en_US/sdk.js";
        fjs.parentNode.insertBefore(js, fjs);
      }(document, 'script', 'facebook-jssdk'));
    </script>


    <!-- Facebook Pixel Code -->
    <script>
    !function(f,b,e,v,n,t,s)
    {if(f.fbq)return;n=f.fbq=function(){n.callMethod?
    n.callMethod.apply(n,arguments):n.queue.push(arguments)};
    if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
    n.queue=[];t=b.createElement(e);t.async=!0;
    t.src=v;s=b.getElementsByTagName(e)[0];
    s.parentNode.insertBefore(t,s)}(window, document,'script',
    'https://connect.facebook.net/en_US/fbevents.js');
    fbq('init', '1629630080621526');
    fbq('track', 'PageView');
    </script>
    <noscript><img height="1" width="1" style="display:none"
    src="https://www.facebook.com/tr?id=1629630080621526&ev=PageView&noscript=1"
    /></noscript>
    <!-- End Facebook Pixel Code -->

  <script src="https://cdn-firebase.inkitt.com/packs/js/firebase-d0c815ac6205ee187784.js" data-ot-ignore="true"></script>
  <script src="https://cdn-firebase.inkitt.com/packs/js/ab_testing-f10d44ba766cf1eb27d2.js" data-ot-ignore="true"></script>
  <script src="https://cdn-firebase.inkitt.com/packs/js/base_story-885f028d6ac382264839.js" data-ot-ignore="true"></script>
  <script src="https://cdn-firebase.inkitt.com/packs/js/story_page-f484cf559f82b1780cd4.js" data-ot-ignore="true"></script>


  <noscript>
  <iframe height='0' src='https://www.googletagmanager.com/ns.html?id=GTM-NHH9V9G' style='display:none;visibility:hidden' width='0'></iframe>
  </noscript>
  <script type='application/ld+json'>
  {
  "@context" : "http://schema.org",
  "@type" : "Organization",
  "name" : "Inkitt",
  "url" : "https://www.inkitt.com",
  "sameAs" : [
  "https://www.facebook.com/inkitt",
  "https://www.twitter.com/inkitt"
  ],
  "logo": "http://www.inkitt.com/1024_onblack-min.png"
  }
  </script>

  <section class='extendedFooter' navbar='true'>
  <div class='extendedFooter_wrap'>
  <div class='extendedFooter_column extendedFooter_column-about'>
  <div class='extendedFooter_title'>
  About Us
  </div>
  <p class='extendedFooter_description'>
  Inkitt is the world’s first reader-powered publisher, providing a platform to discover hidden talents and turn them into globally successful authors. Write captivating stories, read enchanting novels, and we’ll publish the books our readers love most on our sister app, GALATEA and other formats.
  </p>
  </div>
  <div class='extendedFooter_column extendedFooter_column-authors'>
  <div class='extendedFooter_title'>
  Inkitt for Authors
  </div>
  <ul class='extendedFooter_links'>
  <li class='extendedFooter_link'>
  <a target="_self" href="/writing-contests-list">Writing Contests List</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="https://www.inkitt.com/writersblog/how-inkitt-publishes-your-books-from-preparation-to-promotion">Inkitt Publishing</a>
  </li>
  <li class='extendedFooter_link'>
  <a class="js-create-story" href="#">Submit Your Story</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/guidelines">Guidelines</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/groups">Writing Groups</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/author-subscriptions-terms">Author Subscriptions</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="https://inkitt.zendesk.com/hc/en-us/articles/360015784599-What-is-a-DMCA-notice-and-how-to-use-it-">Report Plagiarism</a>
  </li>
  </ul>
  </div>
  <div class='extendedFooter_column extendedFooter_column-readers'>
  <div class='extendedFooter_title'>
  Inkitt for Readers
  </div>
  <ul class='extendedFooter_links'>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/fantasy">Fantasy Books</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/scifi">Sci-Fi Books</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/romance">Romance Books</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/drama">Drama Books</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/thriller">Thriller Books</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/mystery">Mystery Books</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/genres/horror">Horror Books</a>
  </li>
  </ul>
  </div>
  <div class='extendedFooter_column extendedFooter_column-community'>
  <div class='extendedFooter_title'>
  Inkitt Community
  </div>
  <ul class='extendedFooter_links'>
  <li class='extendedFooter_link'>
  <a target="_self" href="/writersblog">The Writer&#39;s Blog</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_blank" rel="noopener" href="https://twitter.com/Inkitt">Twitter</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_blank" rel="noopener" href="https://www.facebook.com/inkitt/">Facebook</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_blank" rel="noopener" href="https://www.instagram.com/inkittbooks/">Instagram</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_blank" rel="noopener" href="https://inkitt.zendesk.com/hc/en-us">Support</a>
  </li>
  <li class='extendedFooter_link'>
  <a target="_self" href="/jobs">Join the Inkitt Team</a>
  </li>
  </ul>
  </div>
  <div class='extendedFooter_column extendedFooter_column-apps'>
  <div class='wrap'>
  <a alt='Download The Inkitt iOS App' class='appBanner' href='https://itunes.apple.com/us/app/inkitt-free-books-fiction/id1033598731?footer_ext' onclick='mixpanelHelper(&#39;user-clicked-download-from-app-store&#39;, { user_id: globalData.currentUser?.id || null, visitor_id: ahoy.getVisitorId(), page_name: document.title, page_url: window.location.href})' rel='noopener' target='_blank'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/images/ios_banner-ef5031be.svg'>
  </a>
  <a alt='Get Inkitt App on Google Play' class='appBanner appBanner-android' href='https://play.google.com/store/apps/details?id=com.inkitt.android.hermione&amp;hl=en&amp;utm_source=website_footer&amp;pcampaignid=MKT-Other-global-all-co-prtnr-py-PartBadge-Mar2515-1' onclick='mixpanelHelper(&#39;user-clicked-download-from-google-play&#39;, { user_id: globalData.currentUser?.id || null, visitor_id: ahoy.getVisitorId(), page_name: document.title, page_url: window.location.href})' rel='noopener' target='_blank'>
  <img loading='lazy' src='https://cdn-firebase.inkitt.com/packs/media/images/android_banner-6dd04511.svg'>
  </a>
  </div>
  </div>
  </div>
  <div class='extendedFooterTrack_wrap'>
  <ul class='extendedFooterTrack_links'>
  <li class='extendedFooterTrack_link'>
  <a target="_self" href="/imprint">Imprint</a>
  </li>
  <li class='extendedFooterTrack_link'>
  <a target="_self" href="/privacy">Privacy Policy</a>
  </li>
  <li class='extendedFooterTrack_link'>
  <a target="_self" href="/terms">Terms</a>
  </li>
  </ul>
  </div>
  </section>

    <script type="text/plain" class="optanon-category-C0002">
      // Google Analytics code begins
      (function(i,s,o,g,r,a,m){i['GoogleAnalyticsObject']=r;i[r]=i[r]||function(){
      (i[r].q=i[r].q||[]).push(arguments)},i[r].l=1*new Date();a=s.createElement(o),
      m=s.getElementsByTagName(o)[0];a.async=1;a.src=g;m.parentNode.insertBefore(a,m)
      })(window,document,'script','//www.google-analytics.com/analytics.js','ga');

      ga('create', 'UA-43855433-1', 'inkitt.com', {'siteSpeedSampleRate': 100});
      ga('set', 'anonymizeIp', true);
      ga('require', 'displayfeatures');
      ga('require', 'GTM-KVJRPWS');
      ga('send', 'pageview');
      // Google Analytics code ends
    </script>

  <script>
    // jQuery(function() {
    //   jQuery.scrollDepth();
    // });
  </script>
  <script defer src="https://static.cloudflareinsights.com/beacon.min.js/vcd15cbe7772f49c399c6a5babf22c1241717689176015" integrity="sha512-ZpsOmlRQV6y907TI0dKBHq9Md29nnaEIPlkf84rnaERnq6zvWvPUqr2ft8M1aS28oN72PdrCzSjY4U6VaAw1EQ==" data-cf-beacon='{"rayId":"8c65a3406cef376b","serverTiming":{"name":{"cfExtPri":true,"cfL4":true}},"version":"2024.8.0","token":"66646d6f5a504ac0bdf45b1c2abfc2c3"}' crossorigin="anonymous"></script>
  </body>
  </html>
  """

inkittcom_story_api_return = """
  {"id":1176584,"title":"Finding me","cover_url":"https://cdn-gcs.inkitt.com/storycovers/efcbe6b2977c949594c8116b902cd73c.jpg","overall_rating":4.804878048780488,"technical_writing_rating":4.341463414634147,"writing_style_rating":4.646341463414634,"plot_rating":4.7560975609756095,"approval_status":"approved-needs-editing","unpublished":false,"staff_approved":false,"featured":false,"category_one":"drama","category_two":null,"age_category":null,"vertical_cover":{"url":"https://cdn-gcs.inkitt.com/vertical_storycovers/0b625cc419c6a8b7b59efd6fa28fdc77.jpg","ipad":{"url":"https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_0b625cc419c6a8b7b59efd6fa28fdc77.jpg"},"iphone":{"url":"https://cdn-gcs.inkitt.com/vertical_storycovers/iphone_0b625cc419c6a8b7b59efd6fa28fdc77.jpg"},"blured":{"url":"https://cdn-gcs.inkitt.com/vertical_storycovers/blured_0b625cc419c6a8b7b59efd6fa28fdc77.jpg"}},"vertical_cover_processing":false,"for_patrons_only":false,"patrons_story_type":"not_applicable","chapters":[{"id":5405826,"chapter_number":1,"name":"Authors note"},{"id":5405854,"chapter_number":2,"name":"Prolgue"},{"id":5405856,"chapter_number":3,"name":"Chapter 1"},{"id":5405858,"chapter_number":4,"name":"Chapter 2"},{"id":5405860,"chapter_number":5,"name":"Chapter 3"},{"id":5405862,"chapter_number":6,"name":"Chapter 4"},{"id":5405864,"chapter_number":7,"name":"Chapter 5"},{"id":5405867,"chapter_number":8,"name":"Chapter 6"},{"id":5405870,"chapter_number":9,"name":"Chapter 7"},{"id":5405897,"chapter_number":10,"name":"Chapter 8"},{"id":5405899,"chapter_number":11,"name":"Chapter 9"},{"id":5405900,"chapter_number":12,"name":"Chapter 10"},{"id":5405901,"chapter_number":13,"name":"Chapter 11 "},{"id":5405902,"chapter_number":14,"name":"Chapter 12"},{"id":5405903,"chapter_number":15,"name":"Chapter 13"},{"id":5405907,"chapter_number":16,"name":"Chapter 14"},{"id":5405909,"chapter_number":17,"name":"Chapter 15"},{"id":5405911,"chapter_number":18,"name":"Chapter 16"},{"id":5405913,"chapter_number":19,"name":"Chapter 17"},{"id":5405919,"chapter_number":20,"name":"Chapter 18"},{"id":5405921,"chapter_number":21,"name":"Chapter 19"},{"id":5405922,"chapter_number":22,"name":"Chapter 20"},{"id":5405923,"chapter_number":23,"name":"Chapter 21"},{"id":5405926,"chapter_number":24,"name":"Chapter 22"},{"id":5405928,"chapter_number":25,"name":"Chapter 23"},{"id":5405931,"chapter_number":26,"name":"Chapter 24"},{"id":5405932,"chapter_number":27,"name":"Chapter 25"},{"id":5405933,"chapter_number":28,"name":"Chapter 26"},{"id":5405937,"chapter_number":29,"name":"Epilogue "}],"user":{"id":3028573,"username":"kyliet","name":"kyliet","small_profile_picture_url":"https://cdn-gcs.inkitt.com/profilepictures/small_17b78a1c8e8d5aadf4911fce06fe077f.jpg","description":null,"first_name":null,"large_profile_picture_url":"https://cdn-gcs.inkitt.com/profilepictures/17b78a1c8e8d5aadf4911fce06fe077f.jpg"},"language":{"id":1,"locale":"en"},"content_labels":[{"id":2,"name":"Assault"},{"id":6,"name":"Child Abuse"},{"id":8,"name":"Domestic Violence"},{"id":9,"name":"Drug Use Overdose"},{"id":1,"name":"Ableism"},{"id":21,"name":"Racism"},{"id":26,"name":"Suicide"}],"test_cover":null,"test_summary":null,"test_title":null,"patron_icon_state":"no_icon","is_liked":false}
  """

inkittcom_story_patreon_return = ("""
  <!DOCTYPE html>
  <html>

  <head>
    <title>Broken Courage (Broken Redemption Book 3) by Ariana Clark at Inkitt</title>
    <link href='https://static-firebase.inkitt.com/manifest.json' rel='manifest'>
    <!-- Open Graph data -->
    <meta content='492061657507324' property='fb:app_id'>
    <link href='https://www.inkitt.com/stories/romance/1271159' rel='canonical'>
    <meta content='index, follow' name='robots'>
    <meta content='BROKEN COURAGE (Broken Redemption Book 3) - Novel by Ariana Clark' property='og:title'>
    <meta content='Ariana Clark' property='author'>
    <meta content='Ariana Clark' name='author'>
    <meta content='article' property='og:type'>
    <meta content='1280' property='og:image:width'>
    <meta content='450' property='og:image:height'>
    <meta content='https://cdn-gcs.inkitt.com/storycovers/be08fe9141a4b513f87f141b61bea2bd.jpg' property='og:image'>
    <meta content='While tortured and held captive as a prisoner of war, she became my reason to keep breathing. The force that fueled my will to fight. To survive.

  When I woke after the rescue to discover the life...' property='og:description'>
    <meta content='Inkitt' property='og:site_name'>
    <meta content='2024-09-19 19:00:01 UTC' property='og:updated_time'>
    <meta content='http://www.inkitt.com/stories/1271159' property='og:url'>
    <meta content='While tortured and held captive as a prisoner of war, she became my reason to keep breathing. The force that fueled my will to fight. To survive.

  When I woke after the rescue to discover the life...' name='description'>
    <!-- Schema.org markup for Google+ -->
    <meta content='https://cdn-gcs.inkitt.com/storycovers/be08fe9141a4b513f87f141b61bea2bd.jpg' itemprop='image'>
    <!-- Twitter Card data -->
    <meta content='summary_large_image' name='twitter:card'>
    <meta content='@inkitt' name='twitter:site'>
    <meta content='BROKEN COURAGE (Broken Redemption Book 3) - Novel by Ariana Clark' name='twitter:title'>
    <meta content='While tortured and held captive as a prisoner of war, she became my reason to keep breathing. The force that fueled my will to fight. To survive.

  When I woke after the rescue to discover the life...' name='twitter:description'>
    <!-- Twitter summary card with large image must be at least 280x150px -->
    <meta content='https://cdn-gcs.inkitt.com/storycovers/be08fe9141a4b513f87f141b61bea2bd.jpg' name='twitter:image:src'>
    <meta content='https://cdn-gcs.inkitt.com/storycovers/be08fe9141a4b513f87f141b61bea2bd.jpg' name='twitter:image'>
    <!-- Pinterest -->
    <!-- / %meta{:content => @story.author.name, :property => "article:author"} -->
    <meta content='2024-05-09 07:08:35 UTC' property='article:published_time'>
    <script type="application/ld+json">{"@context":"http://schema.org","@type":"Article","mainEntityOfPage":{"@type":"WebPage","@id":"https://www.inkitt.com/stories/fanfiction/1271159"},"headline":"BROKEN COURAGE (Broken Redemption Book 3)","image":{"@type":"ImageObject","url":"https://cdn-gcs.inkitt.com/storycovers/be08fe9141a4b513f87f141b61bea2bd.jpg","height":450,"width":1280},"datePublished":"2024-05-09T07:08:35.738Z","dateModified":"2024-09-19T19:00:01.979Z","author":{"@type":"Person","name":"Ariana Clark"},"description":"While tortured and held captive as a prisoner of war, she became my reason to keep breathing. The force that fueled my will to fight. To survive. When I woke after the rescue to discover the life...","publisher":{"@type":"Organization","name":"Inkitt GmbH","logo":{"@type":"ImageObject","url":"https://cdn-firebase.inkitt.com/images/inkitt_door_sign_small.jpg"}}}
  </script>
    <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/base-ac4318c9.css" />
    <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/story_page-60fc35e6.css" />
    <link rel="stylesheet" media="print" href="https://cdn-firebase.inkitt.com/packs/css/block_print-9c951945.css" />
    <link rel="prefetch" media="all"
      href="https://fonts.googleapis.com/css?family=Droid+Serif:400,700,400italic,700italic|Raleway:300,400,500,700&amp;display=swap"
      as="style" />

    <link href='https://cdn-firebase.inkitt.com/packs/media/images/fav_inkitt-4186e304.jpg' rel='icon' type='image/jpeg'>
    <script>
      globalData.storyId = 1271159;
      globalData.inlineCommentsAllowed = true;
      globalData.isAuthorOfCurrentStory = false;
      globalData.chapter = { "id": 5880969, "chapter_number": 1, "name": "Prologue", "comments_count": 1 };
      globalData.previewMode = false;
      globalData.authorPatronTiers = [];
      globalData.currentV2Patronage = null;
      globalData.featuredPatronTierSettings = { "most_popular": false, "patron_tier_id": 3809 }
      globalData.author = { "id": 5789430, "username": "arianaclarkauthor", "name": "Ariana Clark", "description": "Welcome to my world of romantic suspense, where broken characters fight for hope, love, and ultimately their Happily-Ever-After.", "small_profile_picture_url": "https://cdn-gcs.inkitt.com/profilepictures/small_0a8db7b2ff26c197c08e013de9b76247.jpg" };
      globalData.isMobileOrTablet = false;
      globalData.shouldShowPatronOnly = true;
      globalData.authorUsername = "arianaclarkauthor";
      globalData.authorName = "Ariana Clark";
      globalData.isAuthorFollowed = false;
      globalData.isReadingPositionTrackable = true;
    </script>
  </head> """
+ _part1 + """
  <div id='reading-chapter-progress-container'
    props='{&quot;read_progress&quot;:[{&quot;percentage&quot;:1.5891326866936624,&quot;status&quot;:&quot;current&quot;},{&quot;percentage&quot;:1.8822393822393821,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.9870044260288162,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.1682832658442415,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.137677747433845,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.0964780111121573,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.1235521235521237,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.7733308221113098,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.037621244938318,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.4260759016856577,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.606177606177606,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.094123740465204,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.8433939165646482,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.7486109803182974,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.9905358319992466,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.905782088708918,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.4237216310387044,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.8845936528863358,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.8627931066955457,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.9905358319992466,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.9705245315001412,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.3766362180996325,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.109426499670402,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.8798851115924287,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.8751765702985215,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.0729353046426215,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.6268010170449194,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.9375647424427913,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.6826914022035973,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.2141915434598363,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.9481589603540823,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.4095960071569826,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.955221772294943,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.8427818061964403,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.739806008098691,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.495526885770788,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.6727092946605142,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.039975515585272,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.7633487145682267,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.7515773613334589,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.649731613146247,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.7974856389490537,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.1341463414634148,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.391938977304831,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.6091439871927677,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:1.8186740747716357,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:2.662680101704492,&quot;status&quot;:&quot;notread&quot;}]}'>
  </div>
    <div class='page StoryPage'>
      <div class='story-page story-id-1271159' id='page-internal'>
        <div class='story-horizontal-cover'
          data-cover-url='https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_9857f852abe0582e1da4f0d1ba06d180.jpg'
          data-is-test='false' data-summary='While tortured and held captive as a prisoner of war, she became my reason to keep breathing. The force that fueled my will to fight. To survive.

  When I woke after the rescue to discover the life I thought I was coming home to was but a figment of my imagination, hallucinations brought about by pain, desperation, and isolation… it nearly broke me.

  Fifteen years since I first lost her, at last, we have a second chance. Holding her in my arms, finally feeling the warmth of her skin as she melts under my touch, is like a dream. She and her two little girls are now as essential to my existence as the air I breathe.

  However, just as things start falling into place, the universe steps in, threatening to take it all away. I used to think that choosing her cost me everything I’d ever loved, but now I see that in choosing her and her children, I have the chance to reclaim all that I lost. They are my salvation. My true path to redemption.

  Which is why I’ll leave no stone unturned, why I will scorch this world to the ground if that’s what it takes to save them.

  And when I do, I will fight to convince her once and for all they are meant to be mine, just as I was destined to be theirs.
  ' data-test-type='titles' data-title='BROKEN COURAGE (Broken Redemption Book 3)'>
          <div class='story-horizontal-cover__back story-horizontal-cover__back_blurred' itemprop='image'
            style='background-image: url(&#39;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_9857f852abe0582e1da4f0d1ba06d180.jpg&#39;)'>
          </div>
          <div class='story-horizontal-cover__front-wrap'>
            <div id='image-zoom'
              props='{&quot;cover&quot;:{&quot;url&quot;:&quot;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_9857f852abe0582e1da4f0d1ba06d180.jpg&quot;},&quot;storyTitle&quot;:&quot;BROKEN COURAGE (Broken Redemption Book 3)&quot;,&quot;className&quot;:&quot;story-horizontal-cover__front&quot;}'>
            </div>
          </div>
        </div>


        <div class='container'>
          <div class='row no-gutters'>
            <div class='col-2 story-left-side offset-1'>
              <div class='showed-block'>
                <div class='sticky-left-pan' style='display: none'></div>
                <div id='like-story-button'></div>
                <button class='button show-reading-lists-button' id='show-reading-lists-button'>
                  <i class='icon-white icon-bookmark'></i>
                  <span class='big-screen'>
                    Add to Reading List
                  </span>
                  <span class='small-screen'>
                    Reading List
                  </span>
                </button>
                <div id='reading-lists-block-container' props='{&quot;storyId&quot;:1271159}'></div>
                <div style='position: relative'>
                  <div class='write-review-tooltip' style='display: none'>
                    <div class='arrow_box'></div>
                    Ariana Clark would love your feedback! Got a few minutes to write a review?
                    <i class='icon-cancel-1'></i>
                  </div>
                  <a class='button create-review-button' href='/stories/romance/1271159/reviews/new'>
                    Write a Review
                  </a>
                </div>
                <div id='sharing-widget-container'
                  props='{&quot;facebookIcon&quot;:true,&quot;includeTumblr&quot;:true,&quot;name&quot;:&quot;Read BROKEN COURAGE (Broken Redemption Book 3) for free on Inkitt.&quot;,&quot;shareLocation&quot;:&quot;storypage&quot;,&quot;shareUrl&quot;:&quot;https://www.inkitt.com/stories/romance/1271159&quot;,&quot;storyId&quot;:1271159,&quot;disabled&quot;:false}'>
                </div>
                <div id='report-story-button'></div>
                <div id='custom-styling-container'></div>
              </div>
            </div>
            <div class='col-6 story-middle-column'>
              <header class='story-header' data-profile-tracking-source='Story'>
                <h1 class='story-title story-title--big'>
                  BROKEN COURAGE (Broken Redemption Book 3)
                </h1>
                <div class='author-block'>
                  <a class='author-link' data-cta='Profile Picture' href='/arianaclarkauthor' track-profile-click='true'>
                    <img class='profile-picture'
                      src='https://cdn-gcs.inkitt.com/profilepictures/small_0a8db7b2ff26c197c08e013de9b76247.jpg'>
                  </a>
                  <div class='block-1'>
                    <a class='author-link' data-cta='Username' href='/arianaclarkauthor' track-profile-click='true'>
                      <span class='name' id='storyAuthor'>Ariana Clark</span>
                    </a>
                    <a class='stories-count author-link' data-cta='Story Count' href='/arianaclarkauthor'
                      track-profile-click='true'>
                      5 stories
                    </a>
                  </div>
                  <div class='block-2' id='follow-button-container'
                    props='{&quot;user&quot;:{&quot;id&quot;:5789430,&quot;is_followed&quot;:false}}'></div>
                </div>
                <p class='all-rights-reserved'>
                  All Rights Reserved ©
                </p>
                <h2 class='story-author-notes__title'>Story Notes</h2>
                <div class='story-author-notes__text'>
                  <p><b>Welcome to Part 3 of Lucas and Emilia’s love story!!!</b></p>
                  <p><b>BROKEN COURAGE is Book 3 </b>of the Broken Redemption Series which must be read in order. <b>For
                      the best experience be sure to read Book 1 BROKEN VOWS, and Book 2 BROKEN HOPE, before starting this
                      one.</b></p>
                  <p><b>NEW CHAPTERS will post at 3:00 PM EST on Tuesdays &amp; Thursdays!!!</b></p>
                </div>
                <h2>Summary</h2>
                <p class='story-summary'>While tortured and held captive as a prisoner of war, she became my reason to
                  keep breathing. The force that fueled my will to fight. To survive.

                  When I woke after the rescue to discover the life I thought I was coming home to was but a figment of my
                  imagination, hallucinations brought about by pain, desperation, and isolation… it nearly broke me.

                  Fifteen years since I first lost her, at last, we have a second chance. Holding her in my arms, finally
                  feeling the warmth of her skin as she melts under my touch, is like a dream. She and her two little
                  girls are now as essential to my existence as the air I breathe.

                  However, just as things start falling into place, the universe steps in, threatening to take it all
                  away. I used to think that choosing her cost me everything I’d ever loved, but now I see that in
                  choosing her and her children, I have the chance to reclaim all that I lost. They are my salvation. My
                  true path to redemption.

                  Which is why I’ll leave no stone unturned, why I will scorch this world to the ground if that’s what it
                  takes to save them.

                  And when I do, I will fight to convince her once and for all they are meant to be mine, just as I was
                  destined to be theirs.
                </p>
                <div class='dls'>
                  <div class='dlc'>
                    <dl>
                      <dt>Genre:</dt>
                      <dd class='genres'>
                        <a href="/genres/romance">Romance</a> / <a href="/genres/drama">Drama</a>
                      </dd>
                    </dl>
                    <dl>
                      <dt>Author:</dt>
                      <dd><a class="author-link" data-cta="Username in Story Info" track-profile-click="true"
                          href="/arianaclarkauthor">Ariana Clark</a></dd>
                    </dl>
                  </div>
                  <div class='dlc'>
                    <dl>
                      <dt>Status:</dt>
                      <dd>Ongoing</dd>
                    </dl>
                    <dl>
                      <dt>Chapters:</dt>
                      <dd>47</dd>
                    </dl>
                  </div>
                  <div class='dlc'>
                    <dl>
                      <dt>Rating:</dt>
                      <dd class='rating'>
                        <span class='star'>★</span>
                        5.0
                        <a class="show-all-reviews-link" href="/stories/romance/1271159/reviews">4 reviews</a>
                      </dd>
                    </dl>
                    <dl>
                      <dt>Age Rating:</dt>
                      <dd>16+</dd>
                    </dl>
                  </div>
                </div>
              </header>
              <article class='default-style' id='story-text-container' style='font-size: 22px'>
                <h2 class='chapter-head-title'>
                  Prologue
                </h2>
                <div class='' style='position: relative'>
                  <div class='story-page-text' id='chapterText'>
                    <p data-content="278924717"><b>Lucas</b></p>
                    <p data-content="2072265493"><b><i>(17 Days After He Was Rescued)</i></b></p>
                    <p data-content="2692058218">Darkness. It surrounds me on all sides. A cold, black depth that
                      encompasses me like a weighted blanket of nothingness. I would be concerned if not for this
                      lingering sense that maybe I’m better off staying here. Indulging in the calm. Resting in the quiet
                      abyss of emptiness.</p>
                    <p data-content="3620595362">Yet, the desire to surface is a pull I’m not strong enough to fight.
                      Giving in, I follow my awareness as it expands and for the first time, begin wondering how long I’ve
                      been here. Working through my scattered thoughts, I recall brief glimpses of life happening
                      somewhere beyond the obscurity that envelops me now. Bright lights. The whir of machines. People and
                      voices. Blurs of activity happening somewhere off in the distance, far outside the periphery of my
                      existence, as if it were all just a dream.</p>
                    <p data-content="2493067231">Is this what death feels like?</p>
                    <p data-content="2321528877">Except no, that can’t be it, for how else could I explain the physical
                      sensations vacillating through my body like an electric current? While not painful per se, the
                      discomfort is there, registering along the edges of my subconscious. Mild twinges. Hints of dull
                      aches. Sensations that linger on the surface, so barely there, like the pain’s dangling just outside
                      of my reach. I guess I should be relieved, and I would be, if not for this deep-seated void that
                      demands I break free from the numbing fog that’s got me tied down.</p>
                    <p data-content="2849065804">Christ! What is this? This desperate longing for something that’s
                      missing. Or is it someone who’s missing…</p>
                    <p data-content="2945160843">And that’s when it all comes rushing back. Like a tsunami of nightmares,
                      I’m crushed by the weight of the memories until I’m unable to breathe.</p>
                    <p data-content="3791605941">The dank hole they stuck us in…</p>
                    <p data-content="2589018494">The smell of rot, human waste, and desperation…</p>
                    <p data-content="3640360448">The darkness whose depths were so extreme it twisted up my mind and left
                      me questioning if I was even alive.</p>
                    <p data-content="1640306252"><i>God, no!</i></p>
                    <p data-content="4275301431"><i>Is that where I am?</i></p>
                    <p data-content="2655058075"><i>Am I still trapped and fighting to keep breathing?</i></p>
                    <p data-content="2563475572">As if shocked into action, my nervous system recoils. Sensations that
                      barely registered moments ago now flare and magnify until I’m left gasping for air. The pain center
                      in my brain chooses this moment to fire up, mixing with the utter panic in my veins until a tortured
                      scream rips from my cracked lips.</p>
                    <p data-content="1199230158">That’s when I realize I’m awake. With eyes wide open for what feels like
                      the first time, I struggle to get the haziness to clear. Yet even as it does, it’s impossible to see
                      beyond the agonizing pain. It’s everywhere. On my skin and in my bones. In my heart and in my soul.
                      It’s all-encompassing. Inescapable. Overwhelmed and overpowered, painful screams continue to rip
                      through me.</p>
                    <p data-content="1308722176">“Lucas! Son! It’s all right… help! Someone, we need help!”</p>
                    <p data-content="3844357896">I know his voice even before I see him, but try as I might, I don’t have
                      the bandwidth to process his words, never mind that he’s here. The pain. The terror. Waking up in
                      this strange place. It’s all too much input for my battered brain to take. Everything feels off.
                      It’s all wrong.</p>
                    <p data-content="1293828182">Shifting my gaze to take in the space around me, my heart pounds at the
                      sight of the white, fluorescent lighting and stark white walls. I should be relieved to find myself
                      back in the light, but the antiseptic smell mixed with the agonizing sounds coming from my irritated
                      throat makes me wish I was anywhere but here.</p>
                    <p data-content="1913737286">“My wife! Where’s my wife?” I gasp, suddenly remembering my entire reason
                      for surviving this nightmare. “I need her. Embree! Where the fuck is my Embree?” I demand while
                      clawing at the wires on my chest and arms, fighting to untangle myself from everything they’ve got
                      binding me to this bed.</p>
                    <p data-content="2984130417">Before I know what’s happening, I’m surrounded. Arms come from every
                      direction to restrain me, but the adrenaline coursing through my blood amps me up and leaves me
                      fighting for my life.</p>
                    <p data-content="49686313">Because I must get free.</p>
                    <p data-content="1706185597">Because I promised her I’d do whatever it took to come home, and I swear
                      to fucking Christ I WILL make it back to her!</p>
                    <p data-content="1654514038">“Mr. Holt! I’m Dr. Zeller. We need you to calm down! Can you do that for
                      us, please?” The man in the white coat asks, his words frantic as he scans over the others who fight
                      to contain me. “If not, we’ll have to sedate you again.”</p>
                    <p data-content="2098472012">“Fuck you! Where is my wife?” I scream at him, refusing to heed his
                      request, much less answer his questions until he answers mine first. Yet, when my own words come
                      through my ears, I’m shocked by the sound. The break in my voice and the way it comes out like a
                      desperate plea instead of the threatened command I’d intended only adds to my confusion. “What is
                      happening? I need my wife. Someone, please go get my wife!”</p>
                    <p data-content="1680021070">Breaking free, I swing at one of my captors, catching the man’s jaw
                      before I’m restrained against the bed once again. This time, the pain and weakness in my body catch
                      up to me and render me unable to fight back. That the vessel I’ve toned, honed, and developed to be
                      my greatest weapon refuses to comply feels like the ultimate betrayal.</p>
                    <p data-content="2183091640">From the corner of my eye, I catch sight of a woman injecting something
                      into an IV bag that hangs by the top of the bed. Desperate to understand, I follow the lines from
                      the machine and to my horror realize they’re attached to me.</p>
                    <p data-content="283417244">“What did you do?” I growl at her. “What the fuck did you do?”</p>
                    <p data-content="3864583437">Furious at my captors, I scan my surroundings, taking in every face and
                      committing it to memory so I can enact my vengeance once I get free. When my gaze lands on the only
                      face I recognize, it’s the deep look of sorrow in his eyes that gives me pause. In an instant, the
                      fight leaves me but is quickly replaced with a deep sense of dread. Staring at the man who’s like a
                      father to me and seeing the pity and regret radiating from him terrifies me down to my core.</p>
                    <p data-content="192825620">“Pastor, what is happening? Please, just tell me where she is,” I beg,
                      choked up with emotion as despair seeps deep into the dark recesses of my worthless soul.</p>
                    <p data-content="2612098859"><i>I fucking lived!</i></p>
                    <p data-content="2426479005"><i>I gave everything I had to make sure that I survived.</i></p>
                    <p data-content="2535286907"><i>Shouldn’t that be enough?</i></p>
                    <p data-content="2318131759"><i>Aren’t I owed this one thing?</i></p>
                    <p data-content="2512782869">As the tingling numbness from the medication spreads through my blood, I
                      watch as he gives a slight shake of his head and lets out a sad sigh. It’s then that I’m struck by a
                      feeling of déjà vu. Memories of a time gone past assault my senses, and suddenly I remember how he
                      wore that same expression as he tore my heart with the devastating truth. A truth I cannot bear, let
                      alone bring myself to accept, and yet there it is again. Further solidifying this unimaginable
                      reality that leaves me questioning why I’m still here.</p>
                    <p data-content="3882844687">“No! Please God no!” I plead as the weight from this catastrophe rips a
                      sob straight through my chest.</p>
                    <p data-content="291083055"><i>She was my reason for breathing.</i></p>
                    <p data-content="4262769722"><i>For existing.</i></p>
                    <p data-content="478963441"><i>For fighting and surviving.</i></p>
                    <p data-content="2104514336"><i>How the fuck am I supposed to do this without her?</i></p>
                    <p data-content="209879444"><br></p>
                    <p data-content="1995296978"><b><i>Want to read ahead? The next 2 Chapters are available FREE if you
                          FOLLOW ME on REAM!!! (Link in my profile)</i></b></p>
                    <p data-content="2803359878"><b><i>Please remember to LIKE, COMMENT, and REVIEW. For updates on this
                          and future stories, don’t forget to FOLLOW ME.</i></b></p>
                    <p data-content="1600204984">~~~~~~~~~~~~~</p>
                    <p data-content="1983684167"><b>Author’s Note:</b></p>
                    <p data-content="2759500298">This is a small glimpse of what Lucas endured in the aftermath of his
                      rescue, as he struggled to come to terms with what happened and the fact the life he imagined with
                      Embree wasn't real.</p>
                    <p data-content="2246209610"><b>I'd love to hear what you think about this chapter. Can you imagine
                        what it would feel like to survive, only to come home and realize that what he lived for didn't
                        exist?</b></p>
                    <p data-content="3645127142"><span class="ql-cursor">﻿</span>~~~~~~~~~~~~~</p>
                    <p data-content="1127928765"><b><i>NEW CHAPTERS post at 3:00 PM EST on Tuesdays &amp;
                          Thursdays!!!</i></b></p>
                  </div>
                </div>
              </article>
            </div>
            <div class='col-3 story-right-side'>
              <div class='showed-block'>
                <div class='sticky-right-pan'>
                  <div class='chapters-list' style='display: none'>
                    <div class='current-chapter'>
                      <i class='icon-angle-down'></i>
                      <strong>Chapters</strong>
                      <div class='chapter-name'>1. Prologue</div>
                    </div>
                    <ul class='nav nav-list chapter-list-dropdown'>
                      <li class='active'>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/1"><span
                            class='chapter-nr'>
                            1
                          </span>
                          <span class='chapter-title'>
                            Prologue
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/2"><span
                            class='chapter-nr'>
                            2
                          </span>
                          <span class='chapter-title'>
                            Chapter 1
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/3"><span
                            class='chapter-nr'>
                            3
                          </span>
                          <span class='chapter-title'>
                            Chapter 2
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/4"><span
                            class='chapter-nr'>
                            4
                          </span>
                          <span class='chapter-title'>
                            Chapter 3
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/5"><span
                            class='chapter-nr'>
                            5
                          </span>
                          <span class='chapter-title'>
                            Chapter 4
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/6"><span
                            class='chapter-nr'>
                            6
                          </span>
                          <span class='chapter-title'>
                            Chapter 5
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/7"><span
                            class='chapter-nr'>
                            7
                          </span>
                          <span class='chapter-title'>
                            Chapter 6
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/8"><span
                            class='chapter-nr'>
                            8
                          </span>
                          <span class='chapter-title'>
                            Chapter 7
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/9"><span
                            class='chapter-nr'>
                            9
                          </span>
                          <span class='chapter-title'>
                            Chapter 8
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/10"><span
                            class='chapter-nr'>
                            10
                          </span>
                          <span class='chapter-title'>
                            Chapter 9
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/11"><span
                            class='chapter-nr'>
                            11
                          </span>
                          <span class='chapter-title'>
                            Chapter 10
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/12"><span
                            class='chapter-nr'>
                            12
                          </span>
                          <span class='chapter-title'>
                            Chapter 11
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/13"><span
                            class='chapter-nr'>
                            13
                          </span>
                          <span class='chapter-title'>
                            Chapter 12
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/14"><span
                            class='chapter-nr'>
                            14
                          </span>
                          <span class='chapter-title'>
                            Chapter 13
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/15"><span
                            class='chapter-nr'>
                            15
                          </span>
                          <span class='chapter-title'>
                            Chapter 14
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/16"><span
                            class='chapter-nr'>
                            16
                          </span>
                          <span class='chapter-title'>
                            Chapter 15
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/17"><span
                            class='chapter-nr'>
                            17
                          </span>
                          <span class='chapter-title'>
                            Chapter 16
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/18"><span
                            class='chapter-nr'>
                            18
                          </span>
                          <span class='chapter-title'>
                            Chapter 17
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/19"><span
                            class='chapter-nr'>
                            19
                          </span>
                          <span class='chapter-title'>
                            Chapter 18
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/20"><span
                            class='chapter-nr'>
                            20
                          </span>
                          <span class='chapter-title'>
                            Chapter 19
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/21"><span
                            class='chapter-nr'>
                            21
                          </span>
                          <span class='chapter-title'>
                            Chapter 20
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/22"><span
                            class='chapter-nr'>
                            22
                          </span>
                          <span class='chapter-title'>
                            Chapter 21
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/23"><span
                            class='chapter-nr'>
                            23
                          </span>
                          <span class='chapter-title'>
                            Chapter 22
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/24"><span
                            class='chapter-nr'>
                            24
                          </span>
                          <span class='chapter-title'>
                            Chapter 23
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/25"><span
                            class='chapter-nr'>
                            25
                          </span>
                          <span class='chapter-title'>
                            Chapter 24
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/26"><span
                            class='chapter-nr'>
                            26
                          </span>
                          <span class='chapter-title'>
                            Chapter 25
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/27"><span
                            class='chapter-nr'>
                            27
                          </span>
                          <span class='chapter-title'>
                            Chapter 26
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/28"><span
                            class='chapter-nr'>
                            28
                          </span>
                          <span class='chapter-title'>
                            Chapter 27
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/29"><span
                            class='chapter-nr'>
                            29
                          </span>
                          <span class='chapter-title'>
                            Chapter 28
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/30"><span
                            class='chapter-nr'>
                            30
                          </span>
                          <span class='chapter-title'>
                            Chapter 29
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/31"><span
                            class='chapter-nr'>
                            31
                          </span>
                          <span class='chapter-title'>
                            Chapter 30
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/32"><span
                            class='chapter-nr'>
                            32
                          </span>
                          <span class='chapter-title'>
                            Chapter 31
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/33"><span
                            class='chapter-nr'>
                            33
                          </span>
                          <span class='chapter-title'>
                            Chapter 32
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/34"><span
                            class='chapter-nr'>
                            34
                          </span>
                          <span class='chapter-title'>
                            Chapter 33
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/35"><span
                            class='chapter-nr'>
                            35
                          </span>
                          <span class='chapter-title'>
                            Chapter 34
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/36"><span
                            class='chapter-nr'>
                            36
                          </span>
                          <span class='chapter-title'>
                            Chapter 35
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/37"><span
                            class='chapter-nr'>
                            37
                          </span>
                          <span class='chapter-title'>
                            Chapter 36
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/38"><span
                            class='chapter-nr'>
                            38
                          </span>
                          <span class='chapter-title'>
                            Chapter 37
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/39"><span
                            class='chapter-nr'>
                            39
                          </span>
                          <span class='chapter-title'>
                            Chapter 38
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/40"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            40
                          </span>
                          <span class='chapter-title'>
                            Chapter 39
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/41"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            41
                          </span>
                          <span class='chapter-title'>
                            Chapter 40
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/42"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            42
                          </span>
                          <span class='chapter-title'>
                            Chapter 41
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/43"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            43
                          </span>
                          <span class='chapter-title'>
                            Chapter 42
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/44"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            44
                          </span>
                          <span class='chapter-title'>
                            Chapter 43
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/45"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            45
                          </span>
                          <span class='chapter-title'>
                            Chapter 44
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/46"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            46
                          </span>
                          <span class='chapter-title'>
                            Chapter 45
                          </span>
                        </a>
                      </li>
                      <li class=''>
                        <a class="chapter-link" rel="nofollow" href="/stories/romance/1271159/chapters/47"><span
                            class='chapter-patron-icon'>
                            <img class='patrons-icon'
                              src='https://cdn-firebase.inkitt.com/packs/media/images/patrons-icon-a2d37ef7.svg'>
                          </span>
                          <span class='chapter-nr'>
                            47
                          </span>
                          <span class='chapter-title'>
                            Chapter 46
                          </span>
                        </a>
                      </li>
                    </ul>
                  </div>
                </div>
              </div>
            </div>
          </div>
          <div class='row no-gutters'>
            <div class='col-2 story-left-side'></div>
            <div class='col-8 story-middle-column'>
              <a class='inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn' href=''
                id='continue-reading-btn'>Continue Reading</a>
            </div>
            <div class='col-2 story-right-side'></div>
          </div>
          <div class='row no-gutters'>
            <div class='col-2 story-left-side'></div>
            <div class='col-8 story-middle-column'>
              <article class='default-style' id='story-text-container' style='font-size: 22px'>
              </article>
              <div id='follow-modal-position'></div>
              <a class="inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn" target="_self" id="next-chapter-btn"
                href="/stories/romance/1271159/chapters/2">Next Chapter</a>
              <div id='story-post-chapter-reviews'></div>
              <div id='story-comments'></div>
              <div id='author-follow-modal'></div>
            </div>
  """
+ _part2)

inkittcom_story_patreon_api_return = """
  {
      "id": 1271159,
      "title": "BROKEN COURAGE (Broken Redemption Book 3)",
      "cover_url": "https://cdn-gcs.inkitt.com/storycovers/be08fe9141a4b513f87f141b61bea2bd.jpg",
      "overall_rating": 5.0,
      "technical_writing_rating": 4.75,
      "writing_style_rating": 4.75,
      "plot_rating": 5.0,
      "approval_status": "approved-needs-editing",
      "unpublished": false,
      "staff_approved": false,
      "featured": false,
      "category_one": "romance",
      "category_two": "drama",
      "age_category": null,
      "vertical_cover": {
          "url": "https://cdn-gcs.inkitt.com/vertical_storycovers/9857f852abe0582e1da4f0d1ba06d180.jpg",
          "ipad": {
              "url": "https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_9857f852abe0582e1da4f0d1ba06d180.jpg"
          },
          "iphone": {
              "url": "https://cdn-gcs.inkitt.com/vertical_storycovers/iphone_9857f852abe0582e1da4f0d1ba06d180.jpg"
          },
          "blured": {
              "url": "https://cdn-gcs.inkitt.com/vertical_storycovers/blured_9857f852abe0582e1da4f0d1ba06d180.jpg"
          }
      },
      "vertical_cover_processing": false,
      "for_patrons_only": true,
      "patrons_story_type": "some_chapters",
      "chapters": [
          {
              "id": 5880969,
              "chapter_number": 1,
              "name": "Prologue"
          },
          {
              "id": 5898018,
              "chapter_number": 2,
              "name": "Chapter 1"
          },
          {
              "id": 5898045,
              "chapter_number": 3,
              "name": "Chapter 2"
          },
          {
              "id": 5922110,
              "chapter_number": 4,
              "name": "Chapter 3"
          },
          {
              "id": 5922129,
              "chapter_number": 5,
              "name": "Chapter 4"
          },
          {
              "id": 5945425,
              "chapter_number": 6,
              "name": "Chapter 5"
          },
          {
              "id": 5945449,
              "chapter_number": 7,
              "name": "Chapter 6"
          },
          {
              "id": 5970553,
              "chapter_number": 8,
              "name": "Chapter 7"
          },
          {
              "id": 5970583,
              "chapter_number": 9,
              "name": "Chapter 8"
          },
          {
              "id": 5992443,
              "chapter_number": 10,
              "name": "Chapter 9"
          },
          {
              "id": 5992682,
              "chapter_number": 11,
              "name": "Chapter 10"
          },
          {
              "id": 6018869,
              "chapter_number": 12,
              "name": "Chapter 11"
          },
          {
              "id": 6018976,
              "chapter_number": 13,
              "name": "Chapter 12"
          },
          {
              "id": 6040733,
              "chapter_number": 14,
              "name": "Chapter 13"
          },
          {
              "id": 6040775,
              "chapter_number": 15,
              "name": "Chapter 14"
          },
          {
              "id": 6063469,
              "chapter_number": 16,
              "name": "Chapter 15"
          },
          {
              "id": 6063511,
              "chapter_number": 17,
              "name": "Chapter 16"
          },
          {
              "id": 6085663,
              "chapter_number": 18,
              "name": "Chapter 17"
          },
          {
              "id": 6085682,
              "chapter_number": 19,
              "name": "Chapter 18"
          },
          {
              "id": 6109611,
              "chapter_number": 20,
              "name": "Chapter 19"
          },
          {
              "id": 6109620,
              "chapter_number": 21,
              "name": "Chapter 20"
          },
          {
              "id": 6132329,
              "chapter_number": 22,
              "name": "Chapter 21"
          },
          {
              "id": 6132354,
              "chapter_number": 23,
              "name": "Chapter 22"
          },
          {
              "id": 6161940,
              "chapter_number": 24,
              "name": "Chapter 23"
          },
          {
              "id": 6162022,
              "chapter_number": 25,
              "name": "Chapter 24"
          },
          {
              "id": 6173198,
              "chapter_number": 26,
              "name": "Chapter 25"
          },
          {
              "id": 6173205,
              "chapter_number": 27,
              "name": "Chapter 26"
          },
          {
              "id": 6196001,
              "chapter_number": 28,
              "name": "Chapter 27"
          },
          {
              "id": 6196029,
              "chapter_number": 29,
              "name": "Chapter 28"
          },
          {
              "id": 6221826,
              "chapter_number": 30,
              "name": "Chapter 29"
          },
          {
              "id": 6221861,
              "chapter_number": 31,
              "name": "Chapter 30"
          },
          {
              "id": 6248387,
              "chapter_number": 32,
              "name": "Chapter 31"
          },
          {
              "id": 6253313,
              "chapter_number": 33,
              "name": "Chapter 32"
          },
          {
              "id": 6266386,
              "chapter_number": 34,
              "name": "Chapter 33"
          },
          {
              "id": 6266435,
              "chapter_number": 35,
              "name": "Chapter 34"
          },
          {
              "id": 6289892,
              "chapter_number": 36,
              "name": "Chapter 35"
          },
          {
              "id": 6289909,
              "chapter_number": 37,
              "name": "Chapter 36"
          },
          {
              "id": 6302462,
              "chapter_number": 38,
              "name": "Chapter 37"
          },
          {
              "id": 6302548,
              "chapter_number": 39,
              "name": "Chapter 38"
          },
          {
              "id": 6302673,
              "chapter_number": 40,
              "name": "Chapter 39"
          },
          {
              "id": 6302684,
              "chapter_number": 41,
              "name": "Chapter 40"
          },
          {
              "id": 6302701,
              "chapter_number": 42,
              "name": "Chapter 41"
          },
          {
              "id": 6302710,
              "chapter_number": 43,
              "name": "Chapter 42"
          },
          {
              "id": 6302714,
              "chapter_number": 44,
              "name": "Chapter 43"
          },
          {
              "id": 6302719,
              "chapter_number": 45,
              "name": "Chapter 44"
          },
          {
              "id": 6302726,
              "chapter_number": 46,
              "name": "Chapter 45"
          },
          {
              "id": 6318078,
              "chapter_number": 47,
              "name": "Chapter 46"
          }
      ],
      "user": {
          "id": 5789430,
          "username": "arianaclarkauthor",
          "name": "Ariana Clark",
          "small_profile_picture_url": "https://cdn-gcs.inkitt.com/profilepictures/small_0a8db7b2ff26c197c08e013de9b76247.jpg",
          "description": "Welcome to my world of romantic suspense, where broken characters fight for hope, love, and ultimately their Happily-Ever-After.",
          "first_name": "Ariana",
          "large_profile_picture_url": "https://cdn-gcs.inkitt.com/profilepictures/0a8db7b2ff26c197c08e013de9b76247.jpg"
      },
      "language": {
          "id": 1,
          "locale": "en"
      },
      "content_labels": [],
      "test_cover": null,
      "test_summary": null,
      "test_title": null,
      "patron_icon_state": "list",
      "is_liked": false
  }
  """

inkittcom_story_not_a_fic_return = ("""
  <!DOCTYPE html>
  <html>
  <head>
    <title>The Forgotten Twin by Jenn at Inkitt</title>
    <link href='https://static-firebase.inkitt.com/manifest.json' rel='manifest'>
    <!-- Open Graph data -->
    <meta content='492061657507324' property='fb:app_id'>
    <meta content='noindex, follow' name='robots'>
    <meta content='The Forgotten Twin - Free Novella by Jenn' property='og:title'>
    <meta content='Jenn' property='author'>
    <meta content='Jenn' name='author'>
    <meta content='article' property='og:type'>
    <meta content='1280' property='og:image:width'>
    <meta content='450' property='og:image:height'>
    <meta content='https://cdn-gcs.inkitt.com/storycovers/b0b773fea998cd139a991f196664a8d4.jpg' property='og:image'>
    <meta
      content='What if Harry was not only an only child but a twin? Only he did not know of his existence until the day he first entered Hogwarts.'
      property='og:description'>
    <meta content='Inkitt' property='og:site_name'>
    <meta content='2024-07-11 08:41:43 UTC' property='og:updated_time'>
    <meta content='http://www.inkitt.com/stories/73196' property='og:url'>
    <meta
      content='What if Harry was not only an only child but a twin? Only he did not know of his existence until the day he first entered Hogwarts.'
      name='description'>
    <!-- Schema.org markup for Google+ -->
    <meta content='https://cdn-gcs.inkitt.com/storycovers/b0b773fea998cd139a991f196664a8d4.jpg' itemprop='image'>
    <!-- Twitter Card data -->
    <meta content='summary_large_image' name='twitter:card'>
    <meta content='@inkitt' name='twitter:site'>
    <meta content='The Forgotten Twin - Free Novella by Jenn' name='twitter:title'>
    <meta
      content='What if Harry was not only an only child but a twin? Only he did not know of his existence until the day he first entered Hogwarts.'
      name='twitter:description'>
    <!-- Twitter summary card with large image must be at least 280x150px -->
    <meta content='https://cdn-gcs.inkitt.com/storycovers/b0b773fea998cd139a991f196664a8d4.jpg' name='twitter:image:src'>
    <meta content='https://cdn-gcs.inkitt.com/storycovers/b0b773fea998cd139a991f196664a8d4.jpg' name='twitter:image'>
    <!-- Pinterest -->
    <!-- / %meta{:content => @story.author.name, :property => "article:author"} -->
    <meta content='2016-06-08 05:26:43 UTC' property='article:published_time'>
    <script type="application/ld+json">{"@context":"http://schema.org","@type":"Article","mainEntityOfPage":{"@type":"WebPage","@id":"https://www.inkitt.com/stories/drama/73196"},"headline":"The Forgotten Twin","image":{"@type":"ImageObject","url":"https://cdn-gcs.inkitt.com/storycovers/b0b773fea998cd139a991f196664a8d4.jpg","height":450,"width":1280},"datePublished":"2016-06-08T05:26:43.740Z","dateModified":"2024-07-11T08:41:43.590Z","author":{"@type":"Person","name":"Jenn"},"description":"What if Harry was not only an only child but a twin? Only he did not know of his existence until the day he first entered Hogwarts.","publisher":{"@type":"Organization","name":"Inkitt GmbH","logo":{"@type":"ImageObject","url":"https://cdn-firebase.inkitt.com/images/inkitt_door_sign_small.jpg"}}}
    </script>
    <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/base-ac4318c9.css" />
    <link rel="stylesheet" media="all" href="https://cdn-firebase.inkitt.com/packs/css/story_page-60fc35e6.css" />
    <link rel="stylesheet" media="print" href="https://cdn-firebase.inkitt.com/packs/css/block_print-9c951945.css" />
    <link rel="prefetch" media="all"
      href="https://fonts.googleapis.com/css?family=Droid+Serif:400,700,400italic,700italic|Raleway:300,400,500,700&amp;display=swap"
      as="style" />

    <link href='https://cdn-firebase.inkitt.com/packs/media/images/fav_inkitt-4186e304.jpg' rel='icon' type='image/jpeg'>
    <script>
      globalData.storyId = 73196;
      globalData.inlineCommentsAllowed = true;
      globalData.isAuthorOfCurrentStory = false;
      globalData.chapter = { "id": 418318, "chapter_number": 1, "name": "Prologue", "comments_count": 3 };
      globalData.previewMode = false;
      globalData.authorPatronTiers = [];
      globalData.currentV2Patronage = null;
      globalData.featuredPatronTierSettings = null
      globalData.author = { "id": 33620, "username": "Morales", "name": "Jenn", "description": null, "small_profile_picture_url": "http://www.gravatar.com/avatar/b52ba2726e945009b7b3b123fae96669?s=50\u0026d=mm" };
      globalData.isMobileOrTablet = false;
      globalData.shouldShowPatronOnly = true;
      globalData.authorUsername = "Morales";
      globalData.authorName = "Jenn";
      globalData.isAuthorFollowed = false;
      globalData.isReadingPositionTrackable = true;
    </script>
  </head>
  """
+ _part1 + """
  <div id='reading-chapter-progress-container'
    props='{&quot;read_progress&quot;:[{&quot;percentage&quot;:0.4918504565314078,&quot;status&quot;:&quot;current&quot;},{&quot;percentage&quot;:3.2990607749260916,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:9.698349161499621,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:3.573764487350548,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:5.651047798445962,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:5.334484472699684,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:11.071867723621903,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:8.405933600188368,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:8.442560761844963,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:5.674593830939487,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:8.426863406849279,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:15.992988514768594,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:9.674803129006095,&quot;status&quot;:&quot;notread&quot;},{&quot;percentage&quot;:4.261831881327996,&quot;status&quot;:&quot;notread&quot;}]}'>
  </div>
  <div class='page StoryPage'>
    <div class='story-page story-id-73196' id='page-internal'>
      <div class='story-horizontal-cover'
        data-cover-url='https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_f4eb258456c862b0fd227f25187d6cb1.jpg'
        data-is-test='false'
        data-summary='What if Harry was not only an only child but a twin? Only he did not know of his existence until the day he first entered Hogwarts.'
        data-test-type='titles' data-title='The Forgotten Twin'>
        <div class='story-horizontal-cover__back story-horizontal-cover__back_blurred' itemprop='image'
          style='background-image: url(&#39;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_f4eb258456c862b0fd227f25187d6cb1.jpg&#39;)'>
        </div>
        <div class='story-horizontal-cover__front-wrap'>
          <div id='image-zoom'
            props='{&quot;cover&quot;:{&quot;url&quot;:&quot;https://cdn-gcs.inkitt.com/vertical_storycovers/ipad_f4eb258456c862b0fd227f25187d6cb1.jpg&quot;},&quot;storyTitle&quot;:&quot;The Forgotten Twin&quot;,&quot;className&quot;:&quot;story-horizontal-cover__front&quot;}'>
          </div>
        </div>
      </div>


      <div class='container'>
        <div class='row no-gutters'>
          <div class='col-2 story-left-side offset-1'>
            <div class='showed-block'>
              <div class='sticky-left-pan' style='display: none'></div>
              <div id='like-story-button'></div>
              <button class='button show-reading-lists-button' id='show-reading-lists-button'>
                <i class='icon-white icon-bookmark'></i>
                <span class='big-screen'>
                  Add to Reading List
                </span>
                <span class='small-screen'>
                  Reading List
                </span>
              </button>
              <div id='reading-lists-block-container' props='{&quot;storyId&quot;:73196}'></div>
              <div style='position: relative'>
                <div class='write-review-tooltip' style='display: none'>
                  <div class='arrow_box'></div>
                  Jenn would love your feedback! Got a few minutes to write a review?
                  <i class='icon-cancel-1'></i>
                </div>
                <a class='button create-review-button' href='/stories/fanfiction/73196/reviews/new'>
                  Write a Review
                </a>
              </div>
              <div id='sharing-widget-container'
                props='{&quot;facebookIcon&quot;:true,&quot;includeTumblr&quot;:true,&quot;name&quot;:&quot;Read The Forgotten Twin for free on Inkitt.&quot;,&quot;shareLocation&quot;:&quot;storypage&quot;,&quot;shareUrl&quot;:&quot;https://www.inkitt.com/stories/fanfiction/73196&quot;,&quot;storyId&quot;:73196,&quot;disabled&quot;:false}'>
              </div>
              <div id='report-story-button'></div>
              <div id='custom-styling-container'></div>
            </div>
          </div>
          <div class='col-6 story-middle-column'>
            <header class='story-header' data-profile-tracking-source='Story'>
              <h1 class='story-title story-title--big'>
                The Forgotten Twin
              </h1>
              <div class='author-block'>
                <a class='author-link' data-cta='Profile Picture' href='/Morales' track-profile-click='true'>
                  <img class='profile-picture'
                    src='http://www.gravatar.com/avatar/b52ba2726e945009b7b3b123fae96669?s=50&amp;d=mm'>
                </a>
                <div class='block-1'>
                  <a class='author-link' data-cta='Username' href='/Morales' track-profile-click='true'>
                    <span class='name' id='storyAuthor'>Jenn</span>
                  </a>
                  <a class='stories-count author-link' data-cta='Story Count' href='/Morales'
                    track-profile-click='true'>
                    2 stories
                  </a>
                </div>
                <div class='block-2' id='follow-button-container'
                  props='{&quot;user&quot;:{&quot;id&quot;:33620,&quot;is_followed&quot;:false}}'></div>
              </div>
              <h2>Summary</h2>
              <p class='story-summary'>What if Harry was not only an only child but a twin? Only he did not know of his
                existence until the day he first entered Hogwarts.</p>
              <div class='dls'>
                <div class='dlc'>
                  <dl>
                    <dt>Genre:</dt>
                    <dd class='genres'>
                      <a href="/genres/fantasy">Fantasy</a>
                    </dd>
                  </dl>
                  <dl>
                    <dt>Author:</dt>
                    <dd><a class="author-link" data-cta="Username in Story Info" track-profile-click="true"
                        href="/morales">Jenn</a></dd>
                  </dl>
                </div>
                <div class='dlc'>
                  <dl>
                    <dt>Status:</dt>
                    <dd>Complete</dd>
                  </dl>
                  <dl>
                    <dt>Chapters:</dt>
                    <dd>14</dd>
                  </dl>
                </div>
                <div class='dlc'>
                  <dl>
                    <dt>Rating:</dt>
                    <dd class='rating'>
                      <span class='star'>★</span>
                      4.6
                      <a class="show-all-reviews-link" href="/stories/fanfiction/73196/reviews">7 reviews</a>
                    </dd>
                  </dl>
                  <dl>
                    <dt>Age Rating:</dt>
                    <dd>16+</dd>
                  </dl>
                </div>
              </div>
            </header>
            <article class='default-style' id='story-text-container' style='font-size: 22px'>
              <h2 class='chapter-head-title'>
                Prologue
              </h2>
              <div class='' style='position: relative'>
                <div class='story-page-text' id='chapterText'>
                  <p data-content="261088072"><b>[</b><b><i>October 31, 1980</i></b><b>] [</b><b><i>Hogwarts</i></b><b>,
                    </b><b><i>Scotland</i></b><b>]</b></p>
                  <p data-content="2317964631">“Oh, my…” muttered sorrowfully from Professor McGonagall’s lips as she
                    tried to hold back her tears. Hagrid, the half-giant, wasn’t as considerate.</p>
                  <p data-content="4147557757">“I…I’m so sorry!!” Hagrid said as he continues to wipe what looks like
                    never ending tears, never moving from his spot in the middle of their headmaster’s office.</p>
                  <p data-content="275569565">It had only been a couple of minutes since Hagrid delivered the dreadful
                    news but to them the silence seemed like it has been hours. The small group of four that had
                    gathered in Dumbledore’s office having just finished a discussion on moving the Potters before the
                    Dark Lord found out of their address, had ironically been just told of the tragic news of their
                    deaths by a weeping half-giant holding a baby. Needless to say, it was the most inconsolable failure
                    that they had ever had, more so to <i>Hagrid</i>.</p>
                  <p data-content="1088551954">“And the other…?” asked the Headmaster after those few minutes of
                    mournful silence. Professor Snape looked up expectantly to the half-giant. Hagrid, if possible, only
                    wept more.</p>
                  <p data-content="3313974515">“I-I… I <i>lost him</i>.”</p>
                  <p data-content="346758127">“…”</p>
                  <p data-content="346758127">“…”</p>
                  <p data-content="346758127">“…”</p>
                  <p data-content="2090251790">Understandably, no words were needed to be said after.</p>
                  <p data-content="2999779820"><b><i>Tbc</i></b></p>
                </div>
              </div>
            </article>
          </div>
          <div class='col-3 story-right-side'>
            <div class='showed-block'>
              <div class='sticky-right-pan'>
                <div class='chapters-list' style='display: none'>
                  <div class='current-chapter'>
                    <i class='icon-angle-down'></i>
                    <strong>Chapters</strong>
                    <div class='chapter-name'>1. Prologue</div>
                  </div>
                  <ul class='nav nav-list chapter-list-dropdown'>
                    <li class='active'>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/1"><span
                          class='chapter-nr'>
                          1
                        </span>
                        <span class='chapter-title'>
                          Prologue
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/2"><span
                          class='chapter-nr'>
                          2
                        </span>
                        <span class='chapter-title'>
                          The Post
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/3"><span
                          class='chapter-nr'>
                          3
                        </span>
                        <span class='chapter-title'>
                          Diagon Alley
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/4"><span
                          class='chapter-nr'>
                          4
                        </span>
                        <span class='chapter-title'>
                          Hogwarts Express
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/5"><span
                          class='chapter-nr'>
                          5
                        </span>
                        <span class='chapter-title'>
                          The Sorting
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/6"><span
                          class='chapter-nr'>
                          6
                        </span>
                        <span class='chapter-title'>
                          Harry Potter
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/7"><span
                          class='chapter-nr'>
                          7
                        </span>
                        <span class='chapter-title'>
                          Forbidden Corridor
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/8"><span
                          class='chapter-nr'>
                          8
                        </span>
                        <span class='chapter-title'>
                          Halloween
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/9"><span
                          class='chapter-nr'>
                          9
                        </span>
                        <span class='chapter-title'>
                          Quidditch
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/10"><span
                          class='chapter-nr'>
                          10
                        </span>
                        <span class='chapter-title'>
                          Winter Break
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/11"><span
                          class='chapter-nr'>
                          11
                        </span>
                        <span class='chapter-title'>
                          Dragon
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/12"><span
                          class='chapter-nr'>
                          12
                        </span>
                        <span class='chapter-title'>
                          The Forbidden Forest
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/13"><span
                          class='chapter-nr'>
                          13
                        </span>
                        <span class='chapter-title'>
                          The Philosopher&#39;s Stone
                        </span>
                      </a>
                    </li>
                    <li class=''>
                      <a class="chapter-link" rel="nofollow" href="/stories/fanfiction/73196/chapters/14"><span
                          class='chapter-nr'>
                          14
                        </span>
                        <span class='chapter-title'>
                          Home
                        </span>
                      </a>
                    </li>
                  </ul>
                </div>
              </div>
            </div>
          </div>
        </div>
        <div class='row no-gutters'>
          <div class='col-2 story-left-side'></div>
          <div class='col-8 story-middle-column'>
            <a class='inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn' href=''
              id='continue-reading-btn'>Continue Reading</a>
          </div>
          <div class='col-2 story-right-side'></div>
        </div>
        <div class='row no-gutters'>
          <div class='col-2 story-left-side'></div>
          <div class='col-8 story-middle-column'>
            <article class='default-style' id='story-text-container' style='font-size: 22px'>
            </article>
            <div id='follow-modal-position'></div>
            <a class="inkitt-btn inkitt-btn-large inkitt-btn-blue next-chapter-btn" target="_self" id="next-chapter-btn"
              href="/stories/fanfiction/73196/chapters/2">Next Chapter</a>
            <div id='story-post-chapter-reviews'></div>
            <div id='story-comments'></div>
            <div id='author-follow-modal'></div>
          </div>
  """ 
+ _part2)
