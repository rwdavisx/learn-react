import React, { Component } from 'react';
import './external-box.css';

class ExternalBox extends Component {
    constructor(props) {
        super(props);
        this.state = {
            title: this.props.input.title,
            text: this.props.input.text,
            image: this.props.input.image,
            link: this.props.input.link,
        }
    };

    render() {
        return (
            <div className={'container-fluid m-2'}>
                <div className="row justify-content-end" id='share'>
                    <div className='col-10' id='card-link'>
                        <img className="img-fluid" id='card-link-image' src={this.state.image} alt='' />
                        <div id='card-link-content'>
                            <p id='card-link-title'>{this.state.title}</p>
                            <p id='card-link-info'>{this.state.text}</p>
                            <p id='card-link-source'><a href={this.state.link}>{this.state.link}</a></p>
                        </div>
                    </div>
                </div>
            </div>
        );
    };

    handleComment(input) {
        console.log(input);
    };
};

export default ExternalBox;
