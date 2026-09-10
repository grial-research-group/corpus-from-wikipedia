def get_language(language):
    '''Get the language name and its two letter ISO code from an input that can be two letter or three letter ISO code or the full language name.
    
    Returns
        language_name, language_code'''
    import pycountry
    # input is iso 2 letter code or full name of the language, output is name and 2 letter iso code
    if len(language) == 2: # if language is 2 letter iso code
        language_pyc = pycountry.languages.get(alpha_2=language)
        language_code = language_pyc.alpha_2
        language_name = language_pyc.name

    elif len(language) == 3:
        language_pyc = pycountry.languages.get(alpha_3=language)
        language_name = language_pyc.name

        if language_pyc:
            language_code = language_pyc.alpha_2 if hasattr(language_pyc, 'alpha_2') else language_pyc.alpha_3

    elif len(language) > 3: # if language is the name of the language
        for lang in pycountry.languages:
            if lang.name.lower() == language.lower():
                language_pyc = pycountry.languages.get(name=language)
                language_code = language_pyc.alpha_2
                language_name = language_pyc.name

    return language_name, language_code